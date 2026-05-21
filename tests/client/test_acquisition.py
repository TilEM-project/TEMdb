from datetime import datetime

import httpx

from temdb.models import (
    AcquisitionCreate,
    AcquisitionUpdate,
    StorageLocationCreate,
    TileCreate,
)
from temdb.models.acquisition import (
    AcquisitionParams,
    AcquisitionStatus,
    HardwareParams,
)

_HW = {
    "scope_id": "S1",
    "camera_model": "cm",
    "camera_serial": "cs",
    "camera_bit_depth": 16,
    "media_type": "tape",
}
_AP = {
    "magnification": 1000,
    "spot_size": 3,
    "exposure_time": 100,
    "tile_size": [4096, 4096],
    "tile_overlap": 0.1,
    "saved_bit_depth": 8,
}


def _acq_resp(acq_id: str = "ACQ001") -> dict:
    return {
        "acquisition_id": acq_id,
        "montage_id": "M001",
        "specimen_id": "SPEC001",
        "roi_id": "ROI001",
        "acquisition_task_id": "TASK001",
        "hardware_settings": _HW,
        "acquisition_settings": _AP,
        "status": AcquisitionStatus.IMAGING.value,
        "start_time": "2026-01-01T00:00:00",
    }


def _tile_resp(tile_id: str = "TILE001") -> dict:
    return {
        "tile_id": tile_id,
        "acquisition_id": "ACQ001",
        "raster_index": 0,
        "stage_position": {"x": 0.0, "y": 0.0},
        "raster_position": {"row": 0, "col": 0},
        "focus_score": 0.9,
        "min_value": 0.0,
        "max_value": 255.0,
        "mean_value": 128.0,
        "std_value": 10.0,
        "image_path": "/path/tile.tif",
    }


def _new_acq(acq_id: str = "ACQ001") -> AcquisitionCreate:
    return AcquisitionCreate(
        acquisition_id=acq_id,
        montage_id="M001",
        roi_id="ROI001",
        acquisition_task_id="TASK001",
        hardware_settings=HardwareParams(**_HW),
        acquisition_settings=AcquisitionParams(**_AP),
        tilt_angle=0.0,
        lens_correction=False,
    )


def _new_tile(tile_id: str = "TILE001") -> TileCreate:
    return TileCreate(
        tile_id=tile_id,
        raster_index=0,
        stage_position={"x": 0.0, "y": 0.0},
        raster_position={"row": 0, "col": 0},
        focus_score=0.9,
        min_value=0.0,
        max_value=255.0,
        mean_value=128.0,
        std_value=10.0,
        image_path="/path/tile.tif",
    )


async def test_create_serializes_acquisition(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_acq_resp()))
    await client.acquisition.create(_new_acq())
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/acquisitions"
    assert req.body["acquisition_id"] == "ACQ001"
    assert req.body["hardware_settings"]["scope_id"] == "S1"
    assert req.body["acquisition_settings"]["magnification"] == 1000


async def test_list_with_date_filters(client, captured, response_queue):
    response_queue.append(
        httpx.Response(200, json={"acquisitions": [], "metadata": {}})
    )
    await client.acquisition.list(
        start_date=datetime(2026, 1, 1),
        status=AcquisitionStatus.IMAGING,
        limit=10,
    )
    req = captured[-1]
    assert req.path == "/api/v2/acquisitions"
    assert req.params["start_date"] == "2026-01-01T00:00:00"
    assert req.params["status"] == "imaging"
    assert req.params["limit"] == "10"


async def test_get(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_acq_resp()))
    await client.acquisition.get("ACQ001")
    assert captured[-1].path == "/api/v2/acquisitions/ACQ001"


async def test_update_patches(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_acq_resp()))
    await client.acquisition.update("ACQ001", AcquisitionUpdate(tilt_angle=1.5))
    req = captured[-1]
    assert req.method == "PATCH"
    assert req.path == "/api/v2/acquisitions/ACQ001"
    assert req.body == {"tilt_angle": 1.5}


async def test_delete(client, captured):
    await client.acquisition.delete("ACQ001")
    req = captured[-1]
    assert req.method == "DELETE"
    assert req.path == "/api/v2/acquisitions/ACQ001"


async def test_add_tile(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_tile_resp()))
    await client.acquisition.add_tile("ACQ001", _new_tile())
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/acquisitions/ACQ001/tiles"
    assert req.body["tile_id"] == "TILE001"


async def test_get_tiles_with_fields(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={"tiles": [], "metadata": {}}))
    await client.acquisition.get_tiles(
        "ACQ001", cursor="c1", limit=50, fields=["tile_id"]
    )
    req = captured[-1]
    assert req.path == "/api/v2/acquisitions/ACQ001/tiles"
    assert req.params["limit"] == "50"
    assert req.params["cursor"] == "c1"


async def test_get_tile_count(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={"count": 5}))
    await client.acquisition.get_tile_count("ACQ001")
    assert captured[-1].path == "/api/v2/acquisitions/ACQ001/tile-count"


async def test_add_tiles_bulk_posts_list(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={"inserted": 2}))
    await client.acquisition.add_tiles_bulk(
        "ACQ001", [_new_tile("T1"), _new_tile("T2")]
    )
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/acquisitions/ACQ001/tiles/bulk"
    assert isinstance(req.body, list)
    assert [t["tile_id"] for t in req.body] == ["T1", "T2"]


async def test_delete_tile(client, captured):
    await client.acquisition.delete_tile("ACQ001", "TILE001")
    req = captured[-1]
    assert req.method == "DELETE"
    assert req.path == "/api/v2/acquisitions/ACQ001/tiles/TILE001"


async def test_add_storage_location_posts(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_acq_resp()))
    loc = StorageLocationCreate(location_type="s3", base_path="s3://b/p")
    await client.acquisition.add_storage_location("ACQ001", loc)
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/acquisitions/ACQ001/storage-locations"
    assert req.body == {"location_type": "s3", "base_path": "s3://b/p"}


async def test_get_current_storage_location(client, captured, response_queue):
    response_queue.append(
        httpx.Response(
            200,
            json={
                "location_type": "s3",
                "base_path": "s3://b/p",
                "is_current": True,
                "date_added": "2026-01-01T00:00:00",
                "metadata": {},
            },
        )
    )
    await client.acquisition.get_current_storage_location("ACQ001")
    assert captured[-1].path == "/api/v2/acquisitions/ACQ001/current-storage"
