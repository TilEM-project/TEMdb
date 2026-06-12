import pytest
from httpx import AsyncClient
from sqlalchemy import inspect

from temdb.server.ids import uuid7
from temdb.server.sqlmodels import TileSQLModel


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
