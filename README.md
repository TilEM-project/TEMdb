# TEMdb

Metadata database for TEM sample sectioning and image acquisition.

TEMdb tracks the complete TilEM imaging workflow—from specimen sectioning through final tile acquisition. It provides a REST API for managing metadata and a Python SDK for integration with acquisition software and analysis pipelines.

## Data Model

TEMdb models the TilEM pipeline as a hierarchy:

```
Specimen
  └── Block
        └── Cutting Session
              └── Section
                    └── ROI (Region of Interest)
                          └── Acquisition Task
                                └── Acquisition
                                      └── Tile
```

- **Specimen** - Sample prepared for imaging
- **Block** - Physical portion of a specimen prepared for sectioning
- **Cutting Session** - Session where blocks are sectioned
- **Section** - Thin slice placed on a substrate (grid or support film)
- **ROI** - Region within section(s) targeted for imaging
- **Acquisition Task** - Pure imaging plan (no status; replanning supersedes via `superseded_by`)
- **Acquisition** - Imaging run (in-flight or terminal, see status axes below)
- **Tile** - Individual image in the acquisition montage

Cross-cutting entities: **Dataset** (groups tasks/acquisitions/tiles and drives tile partitioning; may nest via `parent_dataset_id`), **Microscope** (instrument registry referenced by acquisitions), and **Lens Correction** (optical distortion correction referenced by montage runs).

ERDs are generated from the SQLAlchemy models by `uv run python generate_schema_diagram.py` — see `docs/schema_erd.md`.

### Acquisition Status Axes

Acquisitions carry three orthogonal status axes instead of a single lifecycle enum:

- `status` - terminal run outcome: `complete` / `aborted` / `failed`. `NULL` means in-flight. Write-once: once set it cannot change.
- `qc_state` - QC review axis: `pending` / `qc_pass` / `qc_fail` / `needs_review`.
- `transfer_state` - data transfer axis: `not_started` / `in_progress` / `complete` / `error`.

`qc_state` and `transfer_state` changes are stamped with `*_updated_at` / `*_updated_by`.

### Lens Corrections

Lens-correction transforms live on the `lens_corrections` table (`shared_transform` JSONB plus `correction_x_uri` / `correction_y_uri` for the per-axis correction fields). Montage runs reference one via `acquisitions.lc_id`. Do not stuff LC data into `calibration_info` — that field is for run-time calibration snapshots only.

## Packages

### temdb-models (`packages/temdb-models/`)

Shared Pydantic models defining the API schema. Provides:
- `*Base` - Core fields for each entity
- `*Create` - Input models for creating entities
- `*Update` - Partial update models
- `*Response` - API response models

```python
from temdb.models import SpecimenCreate, TileCreate, AcquisitionCreate
```

### temdb-client (`packages/temdb-client/`)

Python SDK with an async client for the TEMdb API.

```python
from temdb.client import TEMdbClient
from temdb.models import TileCreate

async with TEMdbClient("https://temdb.example.com") as client:
    specimens = await client.specimen.list()
    await client.acquisition.add_tiles_bulk("ACQ001", [TileCreate(...)])
```

Create and update methods take either the model or its fields as keywords:

```python
await client.specimen.create(SpecimenCreate(specimen_id="S1", description="cortex"))
await client.specimen.create(specimen_id="S1", description="cortex")  # same request
await client.specimen.update("S1", description="new")  # sends only description
```

Passing both a model and keywords raises `TypeError`; a misspelled field raises a pydantic `ValidationError`
before any request is sent.

#### Image transfers

File uploads compute a base64-encoded SHA-256 checksum in bounded chunks, then stream from the file's current
position, unless a `hash` is supplied. The file remains caller-owned. Supply a key for a new image; omit it to
reuse an existing location. Storage options are passed as keywords, not as a `FileObjectRequest`:
Both `put_image()` and `open_image()` accept `protocol`, `server`, `bucket`, and `key` explicitly.
An explicit bucket requires an absolute key (starting with `/`). These options apply to uploads;
downloads use the image's stored location.

```python
with open("image.tif", "rb") as image:
    await client.acquisition.put_image("ACQ001", "M001_r000_c000", image, key="tiles/image.tif")

image_bytes = await client.acquisition.get_image("ACQ001", "M001_r000_c000")
```

Section images use the same helpers on `client.section`, with only the section ID.
Downloads verify the checksum at EOF and raise `temdb.client.TEMdbChecksumError` on mismatch.
Partial reads through `open_image(..., "rb")` do not verify the entire file until EOF is reached.

For low-level URLs, pass `hash` to `put_image_url()`, or `image_hashes={tile_id: checksum, ...}` to
`put_image_urls()` / `all_put_image_urls()`. Upload requests must send `x-amz-checksum-sha256` with the returned
`hash`. Checksums are base64-encoded SHA-256 digests, not hexadecimal strings.

Supplying a known checksum keeps writes streaming directly:

```python
async with client.section.open_image(
    "SEC001", "post_dropoff_image", "wb", hash=known_checksum, size=total_bytes, expiration=600
) as image:
    await image.write(chunk)
```

You can omit `hash` from `open_image(..., "wb", size=...)`; the client then buffers writes in `BytesIO`,
computes the checksum, and uploads only when the context exits successfully.
**Warning: this is inefficient for large images.** It keeps the entire image in memory and adds a full hashing
pass before upload. Supply a known `hash` to avoid buffering, or use `put_image()` on an existing file to limit
memory use. `put_image_url()` still requires a hash because it has no image content to compute one from.
Existing S3 objects need a stored SHA-256 checksum to be downloaded through these endpoints.

### temdb (`packages/temdb/`)

FastAPI server backed by PostgreSQL and SQLAlchemy. Provides:
- REST API at `/api/v2/` for all entities
- SQLAlchemy-based persistence for all server resources

## Development

Requires [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Setup
uv sync
uv run pre-commit install

# Run tests (uses testcontainers for PostgreSQL)
uv run pytest

# Run server with hot reload
uv run --package temdb uvicorn temdb.server.main:app --reload

# Lint and format
uv run ruff check .
uv run ruff format .
```

### Pre-commit Hooks

Install the hooks once per clone with `uv run pre-commit install`; it covers every worktree of the clone. Until
then nothing runs on commit.

Pre-commit hooks run automatically on `git commit`:
- Trailing whitespace and EOF fixes
- YAML/TOML validation
- Ruff linting and formatting
- Debug statement detection
- Regenerating `docs/` (`generate_schema_diagram.py`) and `openapi.json` (`temdb-openapi`) when server or model
  source changes. CI fails if either is stale. If a hook rewrites them, the commit stops: `git add` the regenerated
  files and commit again.

Run manually: `uv run pre-commit run --all-files`

### Migrations

The schema is managed by Alembic (`packages/temdb/migrations/`).

- **Fresh deploy**: `alembic upgrade head` creates the full schema. This runs automatically — `start.sh` invokes it before launching the server, and docker-compose runs it via the one-shot `migrate` service.
- **Local reset**: `docker compose down -v && docker compose up --build`. A pre-Alembic database volume has no `alembic_version` table and must be dropped — Alembic cannot adopt it.
- **Models == migrations** is enforced by `tests/server/test_migrations_apply.py::test_models_match_migrations`, which runs `alembic check` against a migrated database. If you change a model, add a migration or the suite fails.

```bash
# Run migrations manually against a configured database
uv run alembic -c packages/temdb/alembic.ini upgrade head
```

#### Local development (running Alembic against the Docker Postgres)

Alembic reads its database URL from `TEMDB_MIGRATION_URL`, falling back to `database_url` from config. When you run the `alembic` CLI from `packages/temdb/`, the config's `dev.env` is *not* found (it lives at the repo root and is written for Docker networking — `DATABASE_HOST=postgres`, unexpanded `${...}` interpolation). So for host-side commands, set `TEMDB_MIGRATION_URL` explicitly to reach the container's exposed port:

```bash
# Postgres from docker-compose is exposed on localhost:5432 (temdb/temdb)
export TEMDB_MIGRATION_URL="postgresql+asyncpg://temdb:temdb@localhost:5432/temdb"

# Autogenerate a migration after changing a model (compares models vs. live DB)
uv run alembic -c packages/temdb/alembic.ini revision --autogenerate -m "describe change"

# Apply migrations
uv run alembic -c packages/temdb/alembic.ini upgrade head
```

Autogenerate connects to the database and diffs it against the models, so the DB must be running and already at `head` before you generate a new revision.

### Docker

```bash
# Start PostgreSQL + run migrations + start server
docker-compose up

# API: http://localhost:8000
```

### Releasing

Releases are managed via GitHub Actions. To release a new version:

1. Go to **Actions → Release → Run workflow**
2. Select bump type (patch/minor/major)
3. Click **Run workflow**

This runs tests, bumps versions in all packages, updates `uv.lock` and the recorded API contract, creates a git tag, publishes `temdb-models`, `temdb` and `temdb-client` to PyPI, and creates a GitHub release.

For a release candidate, set **version** to the exact version, for example `4.0.0rc0`. Choose **next_rc** to go on to `4.0.0rc1`, and set **version** to `4.0.0` for the final release. Write versions as PyPI does, with no dash.

Installers skip release candidates unless asked, so pin the version to install one: `uv pip install temdb-client==4.0.0rc0`.

## Architecture

```
temdb-models (shared schemas)
       │
   ┌───┴───┐
   ▼       ▼
client   server
```

The server does not depend on the client. Both import from `temdb-models`.

## API Contracts

### Natural keys are immutable

Natural-key ids (`specimen_id`, `block_id`, `section_id`, ...) are immutable once children reference them. Renames are rejected by the `ON UPDATE NO ACTION` foreign key. If an id is wrong, create a new entity via the CRUD endpoints rather than renaming an existing one.

### Extra fields

Every stored record (specimen, block, cutting session, section, substrate, substrate layout, ROI, task, acquisition, tile, dataset, microscope, lens correction) has an `extra` object for fields outside the schema. Unknown top-level fields are still rejected, so a typo fails instead of landing in `extra`.

```python
await client.block.create(block_id="B1", specimen_id="S1", extra={"foo": "bar", "batch": 7})
await client.block.update("S1", "B1", extra={"batch": 8, "foo": None})  # extra == {"batch": 8}
```

- **Create** stores the object as sent, dropping keys whose value is `null`.
- **Update** merges at the top level: sent keys are set, `null` removes a key, keys not sent are kept, and a nested value is replaced whole. Sending `"extra": null` or `{}` changes nothing; clear keys one by one with `null`.
- **Read** returns `extra` as its own field. There is no filtering by `extra` keys yet.
- A key that names one of the record's fields (e.g. `extra={"description": ...}`) is rejected; set the field directly.

`extra` is a staging area, and ideally not a permanent storage for shared data. When a key becomes something services depend on, it should be promoted to a column. Then a migration copies the key into the new column and removes it from `extra`, and clients switch to the field.

### Empty JSON fields

A JSON field with no value reads back as `None`. Passing `None` is not the same as leaving a field out:

```python
section = await client.section.create(
    cutting_session_id="CS1",
    media_id="M1",
    aperture_index=1,
    timestamp=datetime.now(timezone.utc),
    position={"x": 1.0, "y": 2.0},
)
section.optical_images  # None, because it was not passed

await client.section.update(section.section_id, condition="ok")                 # position is kept
await client.section.update(section.section_id, condition="ok", position=None)  # position is cleared
```

- **Create**: both leave the field empty.
- **Update**: leaving a field out keeps it, and `None` clears it. A section's `optical_images` are the exception: delete a stored image through its image route.
- `{}` and `[]` are values, not empty fields.

In SQL, find empty fields with `IS NULL`.

### All writers go through the API

Services must not write to Postgres directly — this includes tilem-ingest when it deploys against TEMdb. `updated_at` and the status-axis stamp columns (`qc_state_updated_at` / `qc_state_updated_by`, `transfer_state_updated_at` / `transfer_state_updated_by`) are maintained by the ORM, not by database triggers. Any future direct-SQL writer must set them explicitly or they will silently go stale.
