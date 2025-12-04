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
- **Acquisition Task** - Planned imaging task with parameters
- **Acquisition** - Completed imaging run
- **Tile** - Individual image in the acquisition montage

## Packages

### temdb-models (`packages/temdb-models/`)

Shared Pydantic models defining the API schema. Provides:
- `*Base` - Core fields for each entity
- `*Create` - Input models for creating entities
- `*Update` - Partial update models
- `*Response` - API response models

```python
from temdb.models import SpecimenCreate, TileCreate, AcquisitionStatus
```

### temdb-client (`packages/temdb-client/`)

Python SDK with async and sync clients for the TEMdb API.

```python
from temdb.client import AsyncTEMdbClient, SyncTEMdbClient
from temdb.models import TileCreate

async with AsyncTEMdbClient("https://temdb.example.com") as client:
    specimens = await client.specimen.list()
    await client.acquisition.add_tiles_bulk("ACQ001", [TileCreate(...)])

with SyncTEMdbClient("https://temdb.example.com") as client:
    specimens = client.specimen.list()
```

### temdb (`packages/temdb/`)

FastAPI server with MongoDB/Beanie ODM backend. Provides:
- REST API at `/api/v2/` for all entities
- Beanie Document models extending shared schemas

## Development

Requires [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
# Setup
uv sync
uv run pre-commit install

# Run tests (uses testcontainers for MongoDB)
uv run pytest

# Run server with hot reload
uv run --package temdb uvicorn temdb.server.main:app --reload

# Lint and format
uv run ruff check .
uv run ruff format .
```

### Pre-commit Hooks

Pre-commit hooks run automatically on `git commit`:
- Trailing whitespace and EOF fixes
- YAML/TOML validation
- Ruff linting and formatting
- Debug statement detection

Run manually: `uv run pre-commit run --all-files`

### Docker

```bash
# Start MongoDB + server + Mongo Express
docker-compose up

# API: http://localhost:8000
# Mongo Express: http://localhost:8081
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
