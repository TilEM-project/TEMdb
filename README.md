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
from temdb.client import AsyncTEMdbClient
from temdb.models import TileCreate

async with AsyncTEMdbClient("https://temdb.example.com") as client:
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

This runs tests, bumps versions in all packages, creates a git tag, and publishes `temdb-models` and `temdb-client` to PyPI.

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

### All writers go through the API

Services must not write to Postgres directly — this includes tilem-ingest when it deploys against TEMdb. `updated_at` and the status-axis stamp columns (`qc_state_updated_at` / `qc_state_updated_by`, `transfer_state_updated_at` / `transfer_state_updated_by`) are maintained by the ORM, not by database triggers. Any future direct-SQL writer must set them explicitly or they will silently go stale.
