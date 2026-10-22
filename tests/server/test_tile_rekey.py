import pytest
from httpx import AsyncClient


def _tile_payload(raster_index: int) -> dict:
    return {
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


@pytest.mark.asyncio
async def test_tiles_keyed_by_run_id_wire_unchanged(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    payload = {
        "raster_index": 7,
        "stage_position": {"x": 1.0, "y": 2.0},
        "raster_position": {"row": 0, "col": 7},
        "focus_score": 0.5,
        "min_value": 0,
        "max_value": 255,
        "mean_value": 128,
        "std_value": 10,
        "image_path": "/path/to/tile_7.tif",
    }
    r = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles", json=payload)
    assert r.status_code == 201
    assert r.json()["acquisition_id"] == acq_id

    listed = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tiles")
    assert listed.status_code == 200
    tiles = listed.json()["tiles"]
    assert len(tiles) == 1
    assert tiles[0]["acquisition_id"] == acq_id
    assert tiles[0]["tile_id"] == "TEST_MONTAGE_001_r000_c007"


@pytest.mark.asyncio
async def test_bulk_tile_ingest_is_idempotent(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    batch = [_tile_payload(i) for i in range(3)]

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
    first = [_tile_payload(i) for i in range(2)]
    r1 = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles/bulk", json=first)
    assert r1.status_code == 200

    overlapping = first + [_tile_payload(2)]
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
    payload = _tile_payload(7)

    r1 = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles", json=payload)
    assert r1.status_code == 201

    r2 = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles", json=payload)
    assert r2.status_code == 409

    count = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tile-count")
    assert count.json()["tile_count"] == 1


@pytest.mark.asyncio
async def test_tile_create_with_tile_id_is_422(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    payload = _tile_payload(0) | {"tile_id": "TILE_OLD_STYLE_123"}
    r = await async_client.post(f"/api/v2/acquisitions/{acq_id}/tiles", json=payload)
    assert r.status_code == 422
