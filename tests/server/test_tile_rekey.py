import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import inspect

from temdb.server.ids import uuid7
from temdb.server.sqlmodels import TileSQLModel


def _tile_payload(raster_index: int, tile_id: str | None = None) -> dict:
    payload = {
        "raster_index": raster_index,
        "stage_position": {"x": 1.0, "y": 2.0},
        "raster_position": {"row": 0, "col": raster_index},
        "focus_score": 0.5,
        "min_value": 0,
        "max_value": 255,
        "mean_value": 128,
        "std_value": 10,
        "image_path": f"/path/to/tile_{raster_index}.tif",
    }
    if tile_id is not None:
        payload["tile_id"] = tile_id
    return payload


def test_tile_row_has_run_id_not_acquisition_string():
    cols = {c.key for c in inspect(TileSQLModel).column_attrs}
    assert "run_id" in cols
    assert "acquisition_id" not in cols
    pk_cols = [c.name for c in inspect(TileSQLModel).mapper.primary_key]
    assert pk_cols == ["dataset_id", "run_id", "raster_index"]


@pytest.mark.asyncio
async def test_tiles_keyed_by_run_id_wire_unchanged(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    tile_id = str(uuid7())
    payload = {
        "tile_id": tile_id,
        "raster_index": 7,
        "stage_position": {"x": 1.0, "y": 2.0},
        "raster_position": {"row": 0, "col": 7},
        "focus_score": 0.5,
        "min_value": 0,
        "max_value": 255,
        "mean_value": 128,
        "std_value": 10,
        "image_path": f"/path/to/{tile_id}.tif",
    }
    r = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles", json=payload)
    assert r.status_code == 201
    assert r.json()["acquisition_id"] == acq_id

    listed = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tiles")
    assert listed.status_code == 200
    tiles = listed.json()["tiles"]
    assert len(tiles) == 1
    assert tiles[0]["acquisition_id"] == acq_id
    assert tiles[0]["tile_id"] == tile_id


@pytest.mark.asyncio
async def test_bulk_tile_ingest_is_idempotent(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    batch = [_tile_payload(i, tile_id=str(uuid7())) for i in range(3)]

    r1 = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles/bulk", json=batch)
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["inserted"] == 3
    assert body1["skipped_existing"] == 0

    r2 = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles/bulk", json=batch)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["total_received"] == 3
    assert body2["inserted"] == 0
    assert body2["skipped_existing"] == len(batch)

    count = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tile-count")
    assert count.json()["tile_count"] == 3


@pytest.mark.asyncio
async def test_bulk_tile_ingest_partial_overlap(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    first = [_tile_payload(i, tile_id=str(uuid7())) for i in range(2)]
    r1 = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles/bulk", json=first)
    assert r1.status_code == 200

    overlapping = first + [_tile_payload(2, tile_id=str(uuid7()))]
    r2 = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles/bulk", json=overlapping)
    assert r2.status_code == 200
    body = r2.json()
    assert body["inserted"] == 1
    assert body["skipped_existing"] == 2

    count = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tile-count")
    assert count.json()["tile_count"] == 3


@pytest.mark.asyncio
async def test_single_tile_duplicate_returns_409(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    payload = _tile_payload(7, tile_id=str(uuid7()))

    r1 = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles", json=payload)
    assert r1.status_code == 201

    r2 = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles", json=payload)
    assert r2.status_code == 409

    count = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tile-count")
    assert count.json()["tile_count"] == 1


@pytest.mark.asyncio
async def test_tile_with_non_uuid_tile_id_rejected_422(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    payload = _tile_payload(0, tile_id="TILE_OLD_STYLE_123")
    r = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_tile_without_tile_id_gets_minted_uuid(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    payload = _tile_payload(0)
    r = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles", json=payload)
    assert r.status_code == 201
    assert uuid.UUID(r.json()["tile_id"])
