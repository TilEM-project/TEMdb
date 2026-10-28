import io
import json
import re
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import httpx
import pytest
from botocore.exceptions import ClientError
from httpx import AsyncClient
from minio.error import S3Error
from sqlalchemy import and_, null, or_, select, update

from temdb.server.config import config
from temdb.server.sqlmodels.acquisition import AcquisitionSQLModel
from temdb.server.sqlmodels.tile import TileSQLModel, format_tile_id

TEST_MAX_BATCH_SIZE = 10
config.max_batch_size = TEST_MAX_BATCH_SIZE


def _tile_payload(raster_index: int) -> dict:
    return {
        "raster_index": raster_index,
        "stage_position": {"x": float(raster_index), "y": float(raster_index + 1)},
        "raster_position": {"row": 0, "col": raster_index},
        "focus_score": 0.8,
        "min_value": 10,
        "max_value": 240,
        "mean_value": 100,
        "std_value": 20,
    }


def _tile_id(montage_id: str, col: int) -> str:
    return f"{montage_id}_r000_c{col:03d}"


@pytest.mark.asyncio
async def test_list_acquisitions(async_client: AsyncClient):
    """Test retrieving a list of acquisitions."""
    response = await async_client.get("/api/v2/acquisitions")
    assert response.status_code == 200
    assert "acquisitions" in response.json()
    assert "metadata" in response.json()


@pytest.mark.asyncio
async def test_list_acquisitions_filtered(
    async_client: AsyncClient,
    test_specimen,
    test_roi,
    test_acquisition_task,
    test_acquisition,
):
    """Test filtering acquisitions."""
    # Filter by specimen_id
    resp_spec = await async_client.get(f"/api/v2/acquisitions?specimen_id={test_specimen.specimen_id}")
    assert resp_spec.status_code == 200
    assert all(a["specimen_id"] == test_specimen.specimen_id for a in resp_spec.json()["acquisitions"])
    assert any(a["acquisition_id"] == test_acquisition.acquisition_id for a in resp_spec.json()["acquisitions"])

    # Filter by roi_id
    resp_roi = await async_client.get(f"/api/v2/acquisitions?roi_id={test_roi.roi_id}")
    assert resp_roi.status_code == 200
    assert all(a["roi_id"] == test_roi.roi_id for a in resp_roi.json()["acquisitions"])
    assert any(a["acquisition_id"] == test_acquisition.acquisition_id for a in resp_roi.json()["acquisitions"])

    # Filter by acquisition_task_id
    resp_task = await async_client.get(f"/api/v2/acquisitions?acquisition_task_id={test_acquisition_task.task_id}")
    assert resp_task.status_code == 200
    assert all(a["acquisition_task_id"] == test_acquisition_task.task_id for a in resp_task.json()["acquisitions"])
    assert any(a["acquisition_id"] == test_acquisition.acquisition_id for a in resp_task.json()["acquisitions"])

    # Filter by status: the seeded acquisition is in flight (status NULL)
    resp_status = await async_client.get("/api/v2/acquisitions?status=in_flight")
    assert resp_status.status_code == 200
    assert all(a["status"] is None for a in resp_status.json()["acquisitions"])
    assert any(a["acquisition_id"] == test_acquisition.acquisition_id for a in resp_status.json()["acquisitions"])


@pytest.fixture
async def acquisitions(test_db_manager, test_acquisition):
    """test_acquisition (1000x) and two later runs of its task at 5000x, oldest first."""
    later = [
        AcquisitionSQLModel(
            acquisition_id=f"{test_acquisition.acquisition_id}_{day}",
            montage_id=f"{test_acquisition.montage_id}_{day}",
            specimen_id=test_acquisition.specimen_id,
            roi_id=test_acquisition.roi_id,
            acquisition_task_id=test_acquisition.acquisition_task_id,
            microscope_id=test_acquisition.microscope_id,
            hardware_settings=test_acquisition.hardware_settings,
            acquisition_settings={**test_acquisition.acquisition_settings, "magnification": 5000},
            start_time=test_acquisition.start_time + timedelta(days=day),
        )
        for day in (1, 2)
    ]
    async with test_db_manager.async_session_factory() as session:
        session.add_all(later)
        await session.commit()
    return [test_acquisition, *later]


@pytest.fixture(params=["/api/v2/acquisitions", "/api/v2/aggregated/acquisitions"])
def list_path(request):
    return request.param


def listed_ids(body: dict) -> list[str]:
    return [item.get("acquisition", item)["acquisition_id"] for item in body["acquisitions"]]


@pytest.mark.asyncio
@pytest.mark.parametrize("sort_by, sort_order", [("start_time", -1), ("start_time", 1), ("acquisition_id", -1)])
async def test_list_acquisitions_cursor(async_client: AsyncClient, acquisitions, list_path, sort_by, sort_order):
    """Following next_cursor visits every acquisition once, in sort order."""
    seen, params = [], {"limit": 2, "sort_by": sort_by, "sort_order": sort_order}
    for _ in acquisitions:
        body = (await async_client.get(list_path, params=params)).json()
        seen += listed_ids(body)
        params["cursor"] = body["metadata"]["next_cursor"]
        if params["cursor"] is None:
            break

    expected = sorted(acquisitions, key=lambda acq: getattr(acq, sort_by), reverse=sort_order == -1)
    assert seen == [acq.acquisition_id for acq in expected]
    assert params["cursor"] is None


@pytest.mark.asyncio
async def test_list_acquisitions_total_count(async_client: AsyncClient, acquisitions, list_path):
    """total_count counts every match, not just the page."""
    response = await async_client.get(list_path, params={"limit": 1})
    assert response.status_code == 200
    assert response.json()["metadata"]["total_count"] == len(acquisitions)


@pytest.mark.asyncio
async def test_list_acquisitions_by_magnification(async_client: AsyncClient, acquisitions):
    response = await async_client.get("/api/v2/acquisitions", params={"magnification": 5000})
    assert response.status_code == 200
    assert set(listed_ids(response.json())) == {acq.acquisition_id for acq in acquisitions[1:]}


@pytest.mark.asyncio
async def test_list_aggregated_acquisitions_by_substrate(async_client: AsyncClient, acquisitions, test_roi):
    url = "/api/v2/aggregated/acquisitions"
    response = await async_client.get(url, params={"substrate_media_id": test_roi.substrate_media_id})
    missing = await async_client.get(url, params={"substrate_media_id": "NO_SUCH_SUBSTRATE"})
    assert set(listed_ids(response.json())) == {acq.acquisition_id for acq in acquisitions}
    assert listed_ids(missing.json()) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("params", [{"sort_by": "end_time"}, {"cursor": 999999}, {"cursor": "x"}])
async def test_list_acquisitions_invalid_page(async_client: AsyncClient, acquisitions, list_path, params):
    response = await async_client.get(list_path, params=params)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_acquisition(
    async_client: AsyncClient, test_specimen, test_roi, test_acquisition_task, test_microscope
):
    """Test creating a new acquisition successfully."""
    acq_id_hr = f"ACQ_CREATE_{int(datetime.now(timezone.utc).timestamp())}"
    montage_id_hr = f"MONTAGE_CREATE_{int(datetime.now(timezone.utc).timestamp())}"
    acquisition_data = {
        "acquisition_id": acq_id_hr,
        "montage_id": montage_id_hr,
        "roi_id": test_roi.roi_id,
        "acquisition_task_id": test_acquisition_task.task_id,
        "microscope_id": test_microscope.microscope_id,
        "hardware_settings": {
            "camera_model": "Test Camera Create",
            "camera_serial": "CR12345",
            "camera_bit_depth": 16,
            "media_type": "tape",
        },
        "acquisition_settings": {
            "magnification": 1500,
            "spot_size": 3,
            "exposure_time": 150,
            "tile_size": [4000, 4000],
            "tile_overlap": 0.15,
            "saved_bit_depth": 8,
        },
        "tilt_angle_deg": 5.0,
    }
    response = await async_client.post("/api/v2/acquisitions", json=acquisition_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["acquisition_id"] == acq_id_hr
    assert response_data["montage_id"] == montage_id_hr
    assert response_data["tilt_angle_deg"] == 5.0
    assert response_data["status"] is None
    assert response_data["run_id"]
    assert isinstance(response_data["id"], int)
    assert response_data["roi_id"] == test_roi.roi_id
    assert response_data["acquisition_task_id"] == test_acquisition_task.task_id
    assert response_data["specimen_id"] == test_specimen.specimen_id

    # await async_client.delete(f"/api/v2/acquisitions/{acq_id_hr}")


@pytest.mark.asyncio
async def test_create_acquisition_invalid_parent(
    async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope
):
    """Test creating an acquisition fails atomically if a parent task doesn't exist."""
    acq_id_hr = f"ACQ_CREATE_INVALID_{int(datetime.now(timezone.utc).timestamp())}"
    invalid_task_id = "NON_EXISTENT_TASK_FOR_ACQ"
    acquisition_data = {
        "acquisition_id": acq_id_hr,
        "montage_id": "MONTAGE_INVALID",
        "roi_id": test_roi.roi_id,
        "acquisition_task_id": invalid_task_id,
        "microscope_id": test_microscope.microscope_id,
        "hardware_settings": {
            "camera_model": "c",
            "camera_serial": "1",
            "camera_bit_depth": 8,
            "media_type": "tape",
        },
        "acquisition_settings": {
            "magnification": 1,
            "spot_size": 1,
            "exposure_time": 1,
            "tile_size": [1, 1],
            "tile_overlap": 0,
            "saved_bit_depth": 8,
        },
        "tilt_angle_deg": 0,
    }
    response = await async_client.post("/api/v2/acquisitions", json=acquisition_data)
    assert response.status_code == 404
    assert f"Acquisition Task '{invalid_task_id}' not found" in response.json()["detail"]

    get_response = await async_client.get(f"/api/v2/acquisitions/{acq_id_hr}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_acquisition(async_client: AsyncClient, test_acquisition):
    """Test retrieving a specific acquisition."""
    response = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["acquisition_id"] == test_acquisition.acquisition_id
    assert response_data["id"] == test_acquisition.id
    assert response_data["specimen_id"] == test_acquisition.specimen_id
    assert response_data["roi_id"] == test_acquisition.roi_id
    assert response_data["acquisition_task_id"] == test_acquisition.acquisition_task_id


@pytest.mark.asyncio
async def test_get_acquisition_not_found(async_client: AsyncClient):
    """Test retrieving a non-existent acquisition."""
    response = await async_client.get("/api/v2/acquisitions/NON_EXISTENT_ACQ")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_acquisition(async_client: AsyncClient, test_acquisition):
    """Test writing the terminal status (old qc-passed maps to status=complete + qc_state=qc_pass)."""
    assert test_acquisition.status is None
    update_data = {"status": "complete"}
    response = await async_client.patch(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}", json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "complete"
    assert response_data["end_time"] is not None  # stamped together with the terminal status
    assert response_data["acquisition_id"] == test_acquisition.acquisition_id

    qc_response = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}", json={"qc_state": "qc_pass"}
    )
    assert qc_response.status_code == 200
    assert qc_response.json()["qc_state"] == "qc_pass"
    assert qc_response.json()["status"] == "complete"


@pytest.mark.asyncio
async def test_acquisition_extra_fields_round_trip(
    async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope
):
    acq_id_hr = f"ACQ_EXTRA_{int(datetime.now(timezone.utc).timestamp())}"
    montage_id_hr = f"MONTAGE_EXTRA_{int(datetime.now(timezone.utc).timestamp())}"
    create_response = await async_client.post(
        "/api/v2/acquisitions",
        json={
            "acquisition_id": acq_id_hr,
            "montage_id": montage_id_hr,
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "microscope_id": test_microscope.microscope_id,
            "hardware_settings": {
                "camera_model": "Test Camera Extra",
                "camera_serial": "EX12345",
                "camera_bit_depth": 16,
                "media_type": "tape",
            },
            "acquisition_settings": {
                "magnification": 2000,
                "spot_size": 2,
                "exposure_time": 120,
                "tile_size": [4096, 4096],
                "tile_overlap": 0.1,
                "saved_bit_depth": 8,
            },
            "tilt_angle_deg": 2.0,
            "extra": {"unknown_create_key": {"create": "acq"}},
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["extra"]["unknown_create_key"] == {"create": "acq"}

    patch_response = await async_client.patch(
        f"/api/v2/acquisitions/{acq_id_hr}",
        json={
            "tilt_angle_deg": 3.0,
            "extra": {"unknown_patch_key": "acq-patch"},
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["extra"]["unknown_patch_key"] == "acq-patch"

    get_response = await async_client.get(f"/api/v2/acquisitions/{acq_id_hr}")
    assert get_response.status_code == 200
    assert get_response.json()["extra"]["unknown_create_key"] == {"create": "acq"}
    assert get_response.json()["extra"]["unknown_patch_key"] == "acq-patch"

    list_response = await async_client.get(f"/api/v2/acquisitions?acquisition_task_id={test_acquisition_task.task_id}")
    assert list_response.status_code == 200
    listed = next(acq for acq in list_response.json()["acquisitions"] if acq["acquisition_id"] == acq_id_hr)
    assert listed["extra"]["unknown_create_key"] == {"create": "acq"}
    assert listed["extra"]["unknown_patch_key"] == "acq-patch"


@pytest.mark.asyncio
async def test_delete_acquisition(async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope):
    """Test deleting an acquisition successfully (when it has no Tiles)."""
    acq_id_hr = f"ACQ_DELETE_{int(datetime.now(timezone.utc).timestamp())}"
    acq_data = {
        "acquisition_id": acq_id_hr,
        "montage_id": "MONTAGE_DELETE",
        "roi_id": test_roi.roi_id,
        "acquisition_task_id": test_acquisition_task.task_id,
        "microscope_id": test_microscope.microscope_id,
        "hardware_settings": {
            "camera_model": "c",
            "camera_serial": "1",
            "camera_bit_depth": 8,
            "media_type": "tape",
        },
        "acquisition_settings": {
            "magnification": 1,
            "spot_size": 1,
            "exposure_time": 1,
            "tile_size": [1, 1],
            "tile_overlap": 0,
            "saved_bit_depth": 8,
        },
        "tilt_angle_deg": 0,
    }
    create_response = await async_client.post("/api/v2/acquisitions", json=acq_data)
    assert create_response.status_code == 201

    # Delete the acquisition
    delete_response = await async_client.delete(f"/api/v2/acquisitions/{acq_id_hr}")
    assert delete_response.status_code == 204

    # Verify it's gone
    get_response = await async_client.get(f"/api/v2/acquisitions/{acq_id_hr}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_acquisition_with_tiles(async_client: AsyncClient, test_acquisition, test_tile):
    """Test that deleting an acquisition fails if it has tiles."""
    response = await async_client.delete(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}")
    assert response.status_code == 409
    response_data = response.json()
    assert response_data["error_code"] == "FOREIGN_KEY_VIOLATION"
    assert response_data["context"]["table"].startswith(TileSQLModel.__tablename__)


@pytest.mark.asyncio
async def test_add_tile_to_acquisition(async_client: AsyncClient, test_acquisition):
    """Test adding a single tile to an acquisition."""
    tile_data = {
        "raster_index": 10,
        "stage_position": {"x": 150.5, "y": 250.5},
        "raster_position": {"row": 1, "col": 0},
        "focus_score": 0.92,
        "min_value": 5,
        "max_value": 250,
        "mean_value": 120,
        "std_value": 30,
        "image": {
            "protocol": "s3",
            "server": "http://localhost:9000",
            "bucket": "images",
            "key": "/path/to/test/tile_10.tif",
        },
    }
    response = await async_client.post(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles", json=tile_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["tile_id"] == "TEST_MONTAGE_001_r001_c000"
    assert response_data["acquisition_id"] == test_acquisition.acquisition_id
    assert response_data["raster_index"] == 10
    assert response_data["acquisition_ref"]["id"] == str(test_acquisition.id)


@pytest.mark.asyncio
async def test_add_tile_with_supertile_raster_position(async_client: AsyncClient, test_acquisition):
    tile_data = {
        "raster_index": 42,
        "stage_position": {"x": 1.5, "y": 2.5},
        "raster_position": {"row": 3, "col": 4},
        "focus_score": 0.5,
        "min_value": 0,
        "max_value": 255,
        "mean_value": 128,
        "std_value": 10,
        "image": {
            "protocol": "s3",
            "server": "http://localhost:9000",
            "bucket": "images",
            "key": "/path/to/test/tile_42.tif",
        },
        "supertile_id": "banana",
        "supertile_raster_position": {"row": 7, "col": 8},
    }
    response = await async_client.post(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles", json=tile_data)
    assert response.status_code == 201, response.text
    assert response.json()["supertile_raster_position"] == {"row": 7, "col": 8}

    read_back = await async_client.get(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/TEST_MONTAGE_001_r003_c004"
    )
    assert read_back.status_code == 200, read_back.text
    assert read_back.json()["supertile_raster_position"] == {"row": 7, "col": 8}


@pytest.mark.asyncio
async def test_add_tiles_to_acquisition_bulk(async_client: AsyncClient, test_acquisition):
    """Test adding multiple tiles in bulk."""
    num_tiles = TEST_MAX_BATCH_SIZE + 5
    tiles_data = []
    for i in range(num_tiles):
        tiles_data.append(
            {
                "raster_index": i,
                "stage_position": {"x": float(i), "y": float(i + 1)},
                "raster_position": {"row": i // 10, "col": i % 10},
                "focus_score": 0.8,
                "min_value": 10,
                "max_value": 240,
                "mean_value": 100,
                "std_value": 20,
                "image": {
                    "protocol": "s3",
                    "server": "http://localhost:9000",
                    "bucket": "images",
                    "key": f"/path/to/bulk/tile_{i}.tif",
                },
            }
        )

    response = await async_client.post(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json=tiles_data,
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["total_received"] == num_tiles
    assert response_data["inserted"] == num_tiles
    assert response_data["skipped_existing"] == 0


@pytest.mark.asyncio
async def test_get_tiles_from_acquisition(async_client: AsyncClient, test_acquisition, test_tile):
    """Test retrieving tiles from an acquisition with pagination."""
    acq_id = test_acquisition.acquisition_id

    response1 = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tiles?limit=1")
    assert response1.status_code == 200
    data1 = response1.json()
    assert "tiles" in data1
    assert "metadata" in data1
    assert isinstance(data1["tiles"], list)
    assert len(data1["tiles"]) <= 1
    assert data1["metadata"]["limit"] == 1
    next_cursor = data1["metadata"]["next_cursor"]

    if len(data1["tiles"]) == 1:
        assert data1["tiles"][0]["tile_id"] == "TEST_MONTAGE_001_r000_c000"
        assert data1["tiles"][0]["acquisition_id"] == acq_id

        assert next_cursor == f"{test_tile.row},{test_tile.col},{test_tile.retake}"

    if next_cursor is not None:
        response2 = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tiles?limit=1&cursor={next_cursor}")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["tiles"]) <= 1


@pytest.mark.asyncio
async def test_get_tiles_from_acquisition_bbox_filter(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    tile_specs = [
        (_tile_id("TEST_MONTAGE_001", 10), 10, 10.0, 10.0),
        (_tile_id("TEST_MONTAGE_001", 11), 11, 25.0, 20.0),
        (_tile_id("TEST_MONTAGE_001", 12), 12, 40.0, 30.0),
    ]
    for _name, raster_index, x, y in tile_specs:
        response = await async_client.post(
            f"/api/v2/acquisitions/{acq_id}/tiles",
            json={
                "raster_index": raster_index,
                "stage_position": {"x": x, "y": y},
                "raster_position": {"row": 0, "col": raster_index},
                "focus_score": 0.9,
                "min_value": 0,
                "max_value": 255,
                "mean_value": 128,
                "std_value": 25,
                "image": {
                    "protocol": "s3",
                    "server": "http://localhost:9000",
                    "bucket": "images",
                    "key": f"/path/to/tile_{raster_index}.tif",
                },
            },
        )
        assert response.status_code == 201

    response = await async_client.get(
        f"/api/v2/acquisitions/{acq_id}/tiles?x_min=20&x_max=45&y_min=15&y_max=35&limit=10"
    )
    assert response.status_code == 200
    tiles = response.json()["tiles"]
    returned_ids = {tile["tile_id"] for tile in tiles}
    assert returned_ids == {tile_specs[1][0], tile_specs[2][0]}


@pytest.mark.asyncio
async def test_get_tiles_from_acquisition_bbox_invalid_range_returns_422(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id

    bad_x = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tiles?x_min=100&x_max=10")
    assert bad_x.status_code == 422
    assert "x_min must be <= x_max" in bad_x.json()["detail"]

    bad_y = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tiles?y_min=100&y_max=10")
    assert bad_y.status_code == 422
    assert "y_min must be <= y_max" in bad_y.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize("bound", ["nan", "inf", "-inf"])
async def test_get_tiles_from_acquisition_bbox_rejects_non_finite_bounds(
    async_client: AsyncClient, test_acquisition, bound
):
    response = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles?x_min={bound}")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_tile_from_acquisition(async_client: AsyncClient, test_acquisition, test_tile):
    """Test retrieving a specific tile from an acquisition."""
    response = await async_client.get(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/TEST_MONTAGE_001_r000_c000"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["tile_id"] == "TEST_MONTAGE_001_r000_c000"
    assert response_data["acquisition_id"] == test_acquisition.acquisition_id
    assert response_data["raster_index"] == test_tile.raster_index


@pytest.mark.asyncio
async def test_get_tile_from_acquisition_not_found(async_client: AsyncClient, test_acquisition):
    """Test retrieving a non-existent tile from an acquisition."""
    response = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/NON_EXISTENT_TILE")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_tile_count(async_client: AsyncClient, test_acquisition, test_tile):
    """Test getting the tile count for an acquisition."""
    response = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tile-count")
    assert response.status_code == 200
    assert response.json()["tile_count"] >= 1


@pytest.mark.asyncio
async def test_delete_tile_from_acquisition(async_client: AsyncClient, test_acquisition):
    """Test deleting a specific tile from an acquisition."""
    tile_id_hr = "TEST_MONTAGE_001_r000_c000"
    tile_data = {
        "raster_index": 50,
        "stage_position": {"x": 0, "y": 0},
        "raster_position": {"row": 0, "col": 0},
        "focus_score": 0,
        "min_value": 0,
        "max_value": 0,
        "mean_value": 0,
        "std_value": 0,
    }
    add_resp = await async_client.post(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles", json=tile_data)
    assert add_resp.status_code == 201

    delete_response = await async_client.delete(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id_hr}"
    )
    assert delete_response.status_code == 204

    get_response = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id_hr}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_update_tile_from_acquisition(async_client: AsyncClient, test_acquisition):
    tile_id_hr = _tile_id("TEST_MONTAGE_001", 3)
    add_resp = await async_client.post(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles",
        json=_tile_payload(3),
    )
    assert add_resp.status_code == 201

    patch_resp = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id_hr}",
        json={
            "stage_position": {"x": 999.0, "y": 1000.0},
            "focus_score": 0.95,
        },
    )
    assert patch_resp.status_code == 200
    patched = patch_resp.json()
    assert patched["tile_id"] == tile_id_hr
    assert patched["stage_position"] == {"x": 999.0, "y": 1000.0, "z": None}
    assert patched["focus_score"] == pytest.approx(0.95)

    get_resp = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id_hr}")
    assert get_resp.status_code == 200
    got = get_resp.json()
    assert got["stage_position"] == {"x": 999.0, "y": 1000.0, "z": None}
    assert got["focus_score"] == pytest.approx(0.95)


@pytest.mark.asyncio
async def test_update_tiles_from_acquisition_bulk(async_client: AsyncClient, test_acquisition):
    tile_id_1 = _tile_id("TEST_MONTAGE_001", 10)
    tile_id_2 = _tile_id("TEST_MONTAGE_001", 11)
    for raster_index in (10, 11):
        add_resp = await async_client.post(
            f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles",
            json=_tile_payload(raster_index),
        )
        assert add_resp.status_code == 201

    patch_resp = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json={
            tile_id_1: {"focus_score": 0.91},
            tile_id_2: {"focus_score": 0.92, "stage_position": {"x": 123.0, "y": 456.0}},
        },
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert len(body) == 2
    by_id = {tile["tile_id"]: tile for tile in body}
    assert by_id[tile_id_1]["focus_score"] == pytest.approx(0.91)
    assert by_id[tile_id_2]["focus_score"] == pytest.approx(0.92)
    assert by_id[tile_id_2]["stage_position"] == {"x": 123.0, "y": 456.0, "z": None}


@pytest.mark.asyncio
async def test_update_tiles_from_acquisition_bulk_missing_tile_returns_404(async_client: AsyncClient, test_acquisition):
    tile_id_hr = _tile_id("TEST_MONTAGE_001", 12)
    add_resp = await async_client.post(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles",
        json=_tile_payload(12),
    )
    assert add_resp.status_code == 201

    missing_id = _tile_id("TEST_MONTAGE_001", 99)
    patch_resp = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json={
            tile_id_hr: {"focus_score": 0.77},
            missing_id: {"focus_score": 0.88},
        },
    )
    assert patch_resp.status_code == 404
    assert "Unable to find tiles" in patch_resp.json()["detail"]


@pytest.mark.asyncio
async def test_delete_tiles_from_acquisition_bulk(async_client: AsyncClient, test_acquisition):
    tile_ids = [_tile_id("TEST_MONTAGE_001", 20 + i) for i in range(2)]
    for i in range(2):
        add_resp = await async_client.post(
            f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles",
            json=_tile_payload(20 + i),
        )
        assert add_resp.status_code == 201

    delete_resp = await async_client.request(
        "DELETE",
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json=tile_ids,
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"requested": 2, "deleted": 2, "not_found": []}

    count_resp = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tile-count")
    assert count_resp.status_code == 200
    assert count_resp.json()["tile_count"] == 0


@pytest.mark.asyncio
async def test_delete_tiles_from_acquisition_all(async_client: AsyncClient, test_acquisition):
    for i in range(3):
        add_resp = await async_client.post(
            f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles",
            json=_tile_payload(30 + i),
        )
        assert add_resp.status_code == 201

    delete_resp = await async_client.delete(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/all",
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"deleted": 3}

    count_resp = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tile-count")
    assert count_resp.status_code == 200
    assert count_resp.json()["tile_count"] == 0


@pytest.mark.asyncio
async def test_get_acquisition_with_full_metadata(async_client: AsyncClient, test_acquisition):
    """Test retrieving an acquisition with complete hierarchy metadata."""
    response = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/metadata")
    assert response.status_code == 200
    response_data = response.json()

    assert "specimen" in response_data
    assert "block" in response_data
    assert "cutting_session" in response_data
    assert "section" in response_data
    assert "substrate" in response_data
    assert "roi" in response_data
    assert "acquisition_task" in response_data
    assert "acquisition" in response_data

    assert response_data["acquisition"]["acquisition_id"] == test_acquisition.acquisition_id
    assert response_data["acquisition"]["roi_id"] == test_acquisition.roi_id

    assert response_data["specimen"]["specimen_id"] == test_acquisition.specimen_id
    assert response_data["roi"]["roi_id"] == test_acquisition.roi_id
    assert response_data["acquisition_task"]["task_id"] == test_acquisition.acquisition_task_id


@pytest.mark.asyncio
async def test_get_acquisition_metadata_not_found(async_client: AsyncClient):
    """Test retrieving metadata for a non-existent acquisition."""
    non_existent_id = "NON_EXISTENT_ACQ_ID"
    response = await async_client.get(f"/api/v2/acquisitions/{non_existent_id}/metadata")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_acquisitions_with_full_metadata(
    async_client: AsyncClient,
    test_acquisition,
    test_specimen,
    test_roi,
):
    """Test retrieving acquisitions list with aggregated metadata."""
    response = await async_client.get("/api/v2/aggregated/acquisitions")
    assert response.status_code == 200
    response_data = response.json()
    assert "acquisitions" in response_data
    assert "metadata" in response_data
    assert isinstance(response_data["acquisitions"], list)

    test_acq_found = None
    for acq in response_data["acquisitions"]:
        if acq["acquisition"]["acquisition_id"] == test_acquisition.acquisition_id:
            test_acq_found = acq
            break

    assert test_acq_found is not None, "Test acquisition not found in aggregated results"

    assert "specimen" in test_acq_found
    assert "block" in test_acq_found
    assert "cutting_session" in test_acq_found
    assert "section" in test_acq_found
    assert "substrate" in test_acq_found
    assert "roi" in test_acq_found
    assert "acquisition_task" in test_acq_found
    assert "acquisition" in test_acq_found

    response_filtered = await async_client.get(
        f"/api/v2/aggregated/acquisitions?specimen_id={test_specimen.specimen_id}"
    )
    assert response_filtered.status_code == 200
    filtered_data = response_filtered.json()
    assert len(filtered_data["acquisitions"]) >= 1

    for acq in filtered_data["acquisitions"]:
        assert acq["specimen"]["specimen_id"] == test_specimen.specimen_id

    response_roi_filtered = await async_client.get(f"/api/v2/aggregated/acquisitions?roi_id={test_roi.roi_id}")
    assert response_roi_filtered.status_code == 200
    roi_filtered_data = response_roi_filtered.json()
    assert len(roi_filtered_data["acquisitions"]) >= 1

    for acq in roi_filtered_data["acquisitions"]:
        assert acq["roi"]["roi_id"] == test_roi.roi_id


@pytest.mark.asyncio
async def test_list_acquisitions_aggregated_pagination(async_client: AsyncClient):
    """Test pagination parameters for aggregated acquisitions endpoint."""
    response = await async_client.get("/api/v2/aggregated/acquisitions?limit=1")
    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data["acquisitions"]) <= 1

    # Verify metadata contains expected pagination info (cursor-based, not offset-based)
    assert "total_count" in response_data["metadata"]
    assert "limit" in response_data["metadata"]
    assert "next_cursor" in response_data["metadata"]


@pytest.mark.asyncio
async def test_acquisition_metadata_endpoints_status_filter(async_client: AsyncClient, test_acquisition):
    """Test filtering by acquisition status in metadata endpoints."""
    response = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/metadata")
    assert response.status_code == 200

    # The seeded acquisition is in flight (status NULL) — selected via the literal 'in_flight'.
    assert test_acquisition.status is None
    response_filtered = await async_client.get("/api/v2/aggregated/acquisitions?status=in_flight")
    assert response_filtered.status_code == 200
    filtered_data = response_filtered.json()

    assert any(
        acq["acquisition"]["acquisition_id"] == test_acquisition.acquisition_id for acq in filtered_data["acquisitions"]
    )
    for acq in filtered_data["acquisitions"]:
        assert acq["acquisition"]["status"] is None


@pytest.mark.asyncio
async def test_add_tiles_bulk_with_gzip(async_client: AsyncClient, test_acquisition):
    """Test that gzip-compressed requests are handled correctly."""
    import gzip

    num_tiles = 100
    tiles_data = []
    for i in range(num_tiles):
        tiles_data.append(
            {
                "raster_index": i + 1000,
                "stage_position": {"x": float(i), "y": float(i + 1)},
                "raster_position": {"row": i // 10, "col": i % 10},
                "focus_score": 0.8,
                "min_value": 10,
                "max_value": 240,
                "mean_value": 100,
                "std_value": 20,
                "image": {
                    "protocol": "s3",
                    "server": "http://localhost:9000",
                    "bucket": "images",
                    "key": f"/path/to/gzip/tile_{i}.tif",
                },
            }
        )

    body = json.dumps(tiles_data).encode("utf-8")
    compressed = gzip.compress(body)

    # Verify compression actually reduced size
    assert len(compressed) < len(body)

    response = await async_client.post(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        content=compressed,
        headers={"Content-Encoding": "gzip", "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["total_received"] == num_tiles
    assert response_data["inserted"] == num_tiles
    assert response_data["skipped_existing"] == 0


@pytest.mark.asyncio
async def test_create_acquisition_with_dataset_then_add_and_read_tile(
    async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope
):
    # Dataset via the API (server resolves size_class from the estimate).
    ds = (
        await async_client.post(
            "/api/v2/datasets",
            json={"name": "ds_e2e", "estimated_tile_count": 1000},
        )
    ).json()

    acq_resp = await async_client.post(
        "/api/v2/acquisitions",
        json={
            "acquisition_id": "ACQ_E2E_001",
            "montage_id": "M_E2E",
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "microscope_id": test_microscope.microscope_id,
            "dataset_id": ds["dataset_id"],
            "hardware_settings": {
                "camera_model": "C",
                "camera_serial": "X",
                "camera_bit_depth": 16,
                "media_type": "tape",
            },
            "acquisition_settings": {
                "magnification": 1000,
                "spot_size": 2,
                "exposure_time": 100,
                "tile_size": [4096, 4096],
                "tile_overlap": 0.1,
                "saved_bit_depth": 8,
            },
            "tilt_angle_deg": 0.0,
        },
    )
    assert acq_resp.status_code == 201
    assert acq_resp.json()["dataset_id"] == ds["dataset_id"]

    add = await async_client.post(
        "/api/v2/acquisitions/ACQ_E2E_001/tiles",
        json={
            "raster_index": 7,
            "stage_position": {"x": 11.5, "y": 22.5},
            "raster_position": {"row": 0, "col": 7},
            "focus_score": 0.9,
            "min_value": 0,
            "max_value": 255,
            "mean_value": 128,
            "std_value": 25,
            "image": {"protocol": "s3", "server": "http://localhost:9000", "bucket": "images", "key": "/p/7.tif"},
        },
    )
    assert add.status_code == 201  # would 409 if dataset_id were not persisted

    got = (await async_client.get("/api/v2/acquisitions/ACQ_E2E_001/tiles/M_E2E_r000_c007")).json()
    assert got["stage_position"] == {"x": 11.5, "y": 22.5, "z": None}
    assert got["raster_position"] == {"row": 0, "col": 7}


@pytest.fixture(scope="function")
async def second_acquisition(
    init_db,
    test_db_manager,
    test_specimen,
    test_roi,
    test_acquisition_task,
    test_dataset,
    test_microscope,
    test_acquisition,
):
    async with test_db_manager.async_session_factory() as session:
        acquisition = AcquisitionSQLModel(
            acquisition_id="TEST_ACQ_002",
            montage_id="TEST_MONTAGE_002",
            specimen_id=test_specimen.specimen_id,
            roi_id=test_roi.roi_id,
            acquisition_task_id=test_acquisition_task.task_id,
            dataset_id=test_dataset.dataset_id,
            hardware_settings=test_acquisition.hardware_settings,
            acquisition_settings=test_acquisition.acquisition_settings,
            microscope_id=test_microscope.microscope_id,
            start_time=datetime.now(timezone.utc),
        )
        session.add(acquisition)
        await session.commit()
        await session.refresh(acquisition)
        yield acquisition


async def _seed_tiles(async_client: AsyncClient, acquisition: AcquisitionSQLModel, count: int) -> list[str]:
    tiles = [_tile_payload(i) for i in range(count)]
    response = await async_client.post(f"/api/v2/acquisitions/{acquisition.acquisition_id}/tiles/bulk", json=tiles)
    assert response.status_code in (200, 201), response.text
    return [_tile_id(acquisition.montage_id, i) for i in range(count)]


async def _tile_count(async_client: AsyncClient, acquisition_id: str) -> int:
    response = await async_client.get(f"/api/v2/acquisitions/{acquisition_id}/tile-count")
    return response.json()["tile_count"]


@pytest.mark.asyncio
async def test_delete_all_tiles_is_scoped_to_one_acquisition(
    async_client: AsyncClient, test_acquisition, second_acquisition
):
    assert test_acquisition.dataset_id == second_acquisition.dataset_id
    await _seed_tiles(async_client, test_acquisition, 3)
    await _seed_tiles(async_client, second_acquisition, 2)

    response = await async_client.delete(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/all")

    assert response.status_code == 200
    assert response.json() == {"deleted": 3}
    assert await _tile_count(async_client, test_acquisition.acquisition_id) == 0
    assert await _tile_count(async_client, second_acquisition.acquisition_id) == 2


@pytest.mark.asyncio
async def test_bulk_delete_cannot_reach_another_acquisitions_tiles(
    async_client: AsyncClient, test_acquisition, second_acquisition
):
    await _seed_tiles(async_client, test_acquisition, 1)
    other_ids = await _seed_tiles(async_client, second_acquisition, 2)

    response = await async_client.request(
        "DELETE", f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk", json=other_ids
    )

    assert response.status_code == 200
    assert response.json() == {"requested": 2, "deleted": 0, "not_found": other_ids}
    assert await _tile_count(async_client, second_acquisition.acquisition_id) == 2


@pytest.mark.asyncio
async def test_bulk_update_cannot_reach_another_acquisitions_tiles(
    async_client: AsyncClient, test_acquisition, second_acquisition
):
    await _seed_tiles(async_client, test_acquisition, 1)
    other_ids = await _seed_tiles(async_client, second_acquisition, 1)

    response = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json={other_ids[0]: {"focus_score": 0.99}},
    )

    assert response.status_code == 404
    read_back = await async_client.get(f"/api/v2/acquisitions/{second_acquisition.acquisition_id}/tiles/{other_ids[0]}")
    assert read_back.json()["focus_score"] == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_bulk_delete_with_an_empty_list_deletes_nothing(async_client: AsyncClient, test_acquisition):
    await _seed_tiles(async_client, test_acquisition, 2)

    response = await async_client.request(
        "DELETE", f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk", json=[]
    )

    assert response.status_code == 422
    assert await _tile_count(async_client, test_acquisition.acquisition_id) == 2


@pytest.mark.asyncio
async def test_bulk_update_leaves_the_batch_untouched_when_one_tile_is_missing(
    async_client: AsyncClient, test_acquisition
):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 2)

    response = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json={tile_ids[0]: {"focus_score": 0.99}, _tile_id("TEST_MONTAGE_001", 99): {"focus_score": 0.99}},
    )

    assert response.status_code == 404
    read_back = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_ids[0]}")
    assert read_back.json()["focus_score"] == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_bulk_delete_deletes_what_exists_and_lists_the_rest(async_client: AsyncClient, test_acquisition):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 3)
    ghost = _tile_id("TEST_MONTAGE_001", 99)

    response = await async_client.request(
        "DELETE",
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json=[tile_ids[0], ghost],
    )

    assert response.status_code == 200
    assert response.json() == {"requested": 2, "deleted": 1, "not_found": [ghost]}
    assert await _tile_count(async_client, test_acquisition.acquisition_id) == 2


@pytest.mark.asyncio
async def test_retried_bulk_delete_reports_nothing_deleted(async_client: AsyncClient, test_acquisition):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 2)
    url = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk"
    await async_client.request("DELETE", url, json=tile_ids)

    response = await async_client.request("DELETE", url, json=tile_ids)

    assert response.status_code == 200
    assert response.json() == {"requested": 2, "deleted": 0, "not_found": tile_ids}


@pytest.mark.asyncio
async def test_bulk_delete_counts_an_id_named_twice_once(async_client: AsyncClient, test_acquisition):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 1)

    response = await async_client.request(
        "DELETE",
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json=[tile_ids[0], tile_ids[0]],
    )

    assert response.status_code == 200
    assert response.json() == {"requested": 1, "deleted": 1, "not_found": []}


@pytest.mark.asyncio
async def test_delete_all_on_an_acquisition_without_tiles_reports_zero(async_client: AsyncClient, test_acquisition):
    response = await async_client.delete(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/all")

    assert response.status_code == 200
    assert response.json() == {"deleted": 0}


async def _finish(async_client: AsyncClient, acquisition_id: str, run_status: str) -> None:
    response = await async_client.patch(f"/api/v2/acquisitions/{acquisition_id}", json={"status": run_status})
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_bulk_delete_409s_on_a_complete_acquisition(async_client: AsyncClient, test_acquisition):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 2)
    await _finish(async_client, test_acquisition.acquisition_id, "complete")

    response = await async_client.request(
        "DELETE", f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk", json=tile_ids
    )

    assert response.status_code == 409, response.text
    assert await _tile_count(async_client, test_acquisition.acquisition_id) == 2


@pytest.mark.asyncio
async def test_delete_all_409s_on_a_complete_acquisition(async_client: AsyncClient, test_acquisition):
    await _seed_tiles(async_client, test_acquisition, 2)
    await _finish(async_client, test_acquisition.acquisition_id, "complete")

    response = await async_client.delete(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/all")

    assert response.status_code == 409, response.text
    assert await _tile_count(async_client, test_acquisition.acquisition_id) == 2


@pytest.mark.asyncio
async def test_single_tile_delete_409s_on_a_complete_acquisition(async_client: AsyncClient, test_acquisition):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 1)
    await _finish(async_client, test_acquisition.acquisition_id, "complete")

    response = await async_client.delete(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_ids[0]}")

    assert response.status_code == 409, response.text
    assert await _tile_count(async_client, test_acquisition.acquisition_id) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("run_status", ["aborted", "failed"])
async def test_tile_deletes_are_allowed_after_an_unsuccessful_run(
    async_client: AsyncClient, test_acquisition, run_status: str
):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 3)
    await _finish(async_client, test_acquisition.acquisition_id, run_status)
    url = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}"

    bulk = await async_client.request("DELETE", f"{url}/tiles/bulk", json=tile_ids[:1])
    everything = await async_client.delete(f"{url}/tiles/all")

    assert bulk.json()["deleted"] == 1
    assert everything.json() == {"deleted": 2}


@pytest.mark.asyncio
async def test_bulk_delete_removes_every_tile_when_all_ids_match(async_client: AsyncClient, test_acquisition):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 3)

    response = await async_client.request(
        "DELETE",
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json=tile_ids[:2],
    )

    assert response.status_code == 200
    assert response.json() == {"requested": 2, "deleted": 2, "not_found": []}
    assert await _tile_count(async_client, test_acquisition.acquisition_id) == 1


_GHOST_TILE = "NO_SUCH_MONTAGE_r000_c000"

_TILE_WRITE_ENDPOINTS = [
    ("PATCH", f"tiles/{_GHOST_TILE}", {"focus_score": 0.5}),
    ("PATCH", "tiles/bulk", {_GHOST_TILE: {"focus_score": 0.5}}),
    ("DELETE", f"tiles/{_GHOST_TILE}", None),
    ("DELETE", "tiles/bulk", [_GHOST_TILE]),
    ("DELETE", "tiles/all", None),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method, suffix, body", _TILE_WRITE_ENDPOINTS)
async def test_tile_writes_404_on_an_unknown_acquisition(async_client: AsyncClient, method: str, suffix: str, body):
    response = await async_client.request(method, f"/api/v2/acquisitions/NO_SUCH_ACQ/{suffix}", json=body)

    assert response.status_code == 404, response.text
    assert "NO_SUCH_ACQ" in response.json()["detail"]


@pytest.mark.asyncio
async def test_single_tile_update_cannot_reach_another_acquisitions_tile(
    async_client: AsyncClient, test_acquisition, second_acquisition
):
    other_ids = await _seed_tiles(async_client, second_acquisition, 1)

    response = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{other_ids[0]}",
        json={"focus_score": 0.99},
    )

    assert response.status_code == 404
    read_back = await async_client.get(f"/api/v2/acquisitions/{second_acquisition.acquisition_id}/tiles/{other_ids[0]}")
    assert read_back.json()["focus_score"] == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_single_tile_delete_cannot_reach_another_acquisitions_tile(
    async_client: AsyncClient, test_acquisition, second_acquisition
):
    other_ids = await _seed_tiles(async_client, second_acquisition, 1)

    response = await async_client.delete(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{other_ids[0]}")

    assert response.status_code == 404
    assert await _tile_count(async_client, second_acquisition.acquisition_id) == 1


@pytest.mark.asyncio
async def test_new_tile_has_no_updated_at(async_client: AsyncClient, test_acquisition):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 1)

    tile = (
        await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_ids[0]}")
    ).json()

    assert tile["created_at"] is not None
    assert tile["updated_at"] is None


@pytest.mark.asyncio
async def test_updating_a_tile_stamps_updated_at(async_client: AsyncClient, test_acquisition):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 1)

    patched = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_ids[0]}",
        json={"focus_score": 0.99},
    )

    assert patched.status_code == 200, patched.text
    assert patched.json()["updated_at"] is not None
    read_back = (
        await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_ids[0]}")
    ).json()
    assert read_back["updated_at"] == patched.json()["updated_at"]


@pytest.mark.asyncio
async def test_bulk_update_stamps_updated_at_on_every_tile(async_client: AsyncClient, test_acquisition):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 2)

    response = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json={tile_id: {"focus_score": 0.99} for tile_id in tile_ids},
    )

    assert response.status_code == 200, response.text
    assert all(tile["updated_at"] is not None for tile in response.json())


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["raster_position", "stage_position"])
async def test_update_tile_rejects_null_for_a_not_null_column(async_client: AsyncClient, test_acquisition, field: str):
    [tile_id] = await _seed_tiles(async_client, test_acquisition, 1)
    url = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id}"

    response = await async_client.patch(url, json={field: None})

    assert response.status_code == 422, response.text
    assert [err["loc"][-1] for err in response.json()["context"]["errors"]] == [field]
    assert (await async_client.get(url)).status_code == 200


@pytest.mark.asyncio
async def test_bulk_update_rejects_null_for_a_not_null_column(async_client: AsyncClient, test_acquisition):
    tile_ids = await _seed_tiles(async_client, test_acquisition, 2)
    base = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles"

    response = await async_client.patch(
        f"{base}/bulk",
        json={tile_ids[0]: {"focus_score": 0.5}, tile_ids[1]: {"raster_position": None}},
    )

    assert response.status_code == 422, response.text
    for tile_id in tile_ids:
        got = await async_client.get(f"{base}/{tile_id}")
        assert got.status_code == 200
        assert got.json()["focus_score"] == pytest.approx(0.8)  # the whole batch was refused


@pytest.mark.asyncio
async def test_tile_without_stats_is_stored_and_read_back(async_client: AsyncClient, test_acquisition):
    base = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles"
    tile = _tile_payload(0)
    for field in ("focus_score", "min_value", "max_value", "mean_value", "std_value"):
        del tile[field]

    response = await async_client.post(f"{base}/bulk", json=[tile])
    assert response.status_code in (200, 201), response.text

    got = await async_client.get(f"{base}/{_tile_id('TEST_MONTAGE_001', 0)}")
    assert got.status_code == 200, got.text
    assert got.json()["focus_score"] is None


@pytest.mark.asyncio
async def test_update_tile_clears_a_stat_with_null(async_client: AsyncClient, test_acquisition):
    [tile_id] = await _seed_tiles(async_client, test_acquisition, 1)
    url = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id}"

    response = await async_client.patch(url, json={"focus_score": None})

    assert response.status_code == 200, response.text
    got = await async_client.get(url)
    assert got.status_code == 200, got.text
    assert got.json()["focus_score"] is None


@pytest.mark.asyncio
async def test_focus_scores_lists_a_tile_without_a_score(async_client: AsyncClient, test_acquisition):
    acquisition_id = test_acquisition.acquisition_id
    tile_ids = await _seed_tiles(async_client, test_acquisition, 2)
    await async_client.patch(f"/api/v2/acquisitions/{acquisition_id}/tiles/{tile_ids[1]}", json={"focus_score": None})

    response = await async_client.get(f"/api/v2/qc/{acquisition_id}/focus-scores")

    assert response.status_code == 200, response.text
    body = response.json()
    assert [tile["focus_score"] for tile in body["focus_scores"]] == [pytest.approx(0.8), None]
    assert body["mean_focus"] == pytest.approx(0.8)


@pytest.mark.asyncio
async def test_bulk_upload_large_tile_batch(async_client: AsyncClient, test_acquisition):
    tiles = [_tile_payload(i) for i in range(4096)]
    matcher = {
        "row": 0,
        "col": 1,
        "dX": 1.5,
        "dY": -2.0,
        "dXsd": 0.1,
        "dYsd": 0.2,
        "distance": 3.0,
        "rotation": 0.01,
        "match_quality": 0.9,
        "position": "left",
        "pX": [1.0, 2.0],
        "pY": [3.0],
        "qX": [4.0],
        "qY": [5.0],
    }
    tiles[0].update(matcher=[matcher], supertile_id="ST_0", supertile_raster_position={"row": 1, "col": 2})
    tiles[1].update(focus_score=None, std_value=None)
    base = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles"

    response = await async_client.post(f"{base}/bulk", json=tiles)

    assert response.status_code == 200, response.text
    assert response.json()["inserted"] == 4096
    assert await _tile_count(async_client, test_acquisition.acquisition_id) == 4096
    first = (await async_client.get(f"{base}/{_tile_id('TEST_MONTAGE_001', 0)}")).json()
    assert first["matcher"] == [matcher]
    assert (first["supertile_id"], first["supertile_raster_position"]) == ("ST_0", {"row": 1, "col": 2})
    second = (await async_client.get(f"{base}/{_tile_id('TEST_MONTAGE_001', 1)}")).json()
    assert (second["focus_score"], second["std_value"], second["mean_value"]) == (None, None, 100)
    last = (await async_client.get(f"{base}/{_tile_id('TEST_MONTAGE_001', 4095)}")).json()
    assert last["stage_position"] == {"x": 4095.0, "y": 4096.0, "z": None}
    assert last["raster_position"] == {"row": 0, "col": 4095}
    assert last["image"] is None


@pytest.mark.asyncio
async def test_bulk_update_returns_only_this_acquisitions_tiles(
    async_client: AsyncClient, test_acquisition, second_acquisition
):
    for acquisition in (test_acquisition, second_acquisition):
        response = await async_client.post(
            f"/api/v2/acquisitions/{acquisition.acquisition_id}/tiles", json=_tile_payload(0)
        )
        assert response.status_code == 201

    response = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json={_tile_id("TEST_MONTAGE_001", 0): {"focus_score": 0.1}},
    )

    assert response.status_code == 200
    assert [tile["focus_score"] for tile in response.json()] == [pytest.approx(0.1)]


@pytest.mark.asyncio
async def test_bulk_tile_requests_accept_more_ids_than_one_statement_can_bind(
    async_client: AsyncClient, test_acquisition
):
    await _seed_tiles(async_client, test_acquisition, 1)
    ghosts = [f"TEST_MONTAGE_001_r{i // 100:03d}_c{i % 100:03d}" for i in range(1, 33001)]
    base = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk"

    deleted = await async_client.request("DELETE", base, json=ghosts)
    patched = await async_client.patch(base, json={ghost: {"focus_score": 0.1} for ghost in ghosts})

    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["deleted"] == 0
    assert patched.status_code == 404, patched.text


@pytest.mark.asyncio
@pytest.mark.parametrize("suffix", ["tiles", "tiles/bulk"])
async def test_upload_into_an_archived_dataset_is_a_409(async_client: AsyncClient, test_acquisition, suffix: str):
    archived = await async_client.patch(f"/api/v2/datasets/{test_acquisition.dataset_id}", json={"status": "archived"})
    assert archived.status_code == 200, archived.text
    payload = _tile_payload(0)

    response = await async_client.post(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/{suffix}",
        json=[payload] if suffix == "tiles/bulk" else payload,
    )

    assert response.status_code == 409, response.text
    assert await _tile_count(async_client, test_acquisition.acquisition_id) == 0


@pytest.mark.asyncio
async def test_empty_tile_patches_are_a_422(async_client: AsyncClient, test_acquisition):
    [tile_id] = await _seed_tiles(async_client, test_acquisition, 1)
    base = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles"

    single = await async_client.patch(f"{base}/{tile_id}", json={})
    bulk_empty = await async_client.patch(f"{base}/bulk", json={})
    bulk_entry_empty = await async_client.patch(f"{base}/bulk", json={tile_id: {}})

    assert [single.status_code, bulk_empty.status_code, bulk_entry_empty.status_code] == [422, 422, 422]


def _with_raw_number(payload, path: tuple, token: str) -> bytes:
    marker = "__RAW_NUMBER__"
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = marker
    return json.dumps(payload).replace(f'"{marker}"', token).encode()


@pytest.mark.asyncio
@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
async def test_non_finite_tile_values_are_a_422_and_change_nothing(
    async_client: AsyncClient, test_acquisition, token: str
):
    [tile_id] = await _seed_tiles(async_client, test_acquisition, 1)
    base = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles"
    headers = {"Content-Type": "application/json"}

    requests = {
        "single create": ("POST", base, _with_raw_number(_tile_payload(5), ("focus_score",), token)),
        "bulk create": (
            "POST",
            f"{base}/bulk",
            _with_raw_number([_tile_payload(6)], (0, "stage_position", "x"), token),
        ),
        "single update": ("PATCH", f"{base}/{tile_id}", _with_raw_number({"focus_score": 0}, ("focus_score",), token)),
        "bulk update": (
            "PATCH",
            f"{base}/bulk",
            _with_raw_number({tile_id: {"mean_value": 0}}, (tile_id, "mean_value"), token),
        ),
    }
    statuses = {
        name: (await async_client.request(method, url, content=body, headers=headers)).status_code
        for name, (method, url, body) in requests.items()
    }

    assert statuses == dict.fromkeys(requests, 422)
    assert await _tile_count(async_client, test_acquisition.acquisition_id) == 1
    stored = (await async_client.get(f"{base}/{tile_id}")).json()
    assert (stored["focus_score"], stored["mean_value"]) == (pytest.approx(0.8), 100)


def _image_tile_condition(tile_id):
    match = re.fullmatch(r"(.*)_r(\d+)_c(\d+)(?:_a(\d+))?", tile_id)
    assert match is not None, tile_id
    return and_(
        TileSQLModel.run_id.in_(select(AcquisitionSQLModel.run_id).where(AcquisitionSQLModel.montage_id == match[1])),
        TileSQLModel.row == int(match[2]),
        TileSQLModel.col == int(match[3]),
        TileSQLModel.retake == int(match[4] or 0),
    )


def _tile_image(key: str) -> dict[str, str]:
    return {"protocol": "s3", "server": "http://localhost:9000", "bucket": "tiles", "key": key}


def _image_tile_payload(tile_id: str, raster_index: int, *, include_image: bool = True) -> dict:
    return {
        "raster_index": raster_index,
        "stage_position": {"x": float(raster_index), "y": float(raster_index + 1)},
        "raster_position": {"row": 0, "col": raster_index},
        "focus_score": 0.8,
        "min_value": 10,
        "max_value": 240,
        "mean_value": 100,
        "std_value": 20,
        "image": _tile_image(f"path/to/{tile_id}.tif") if include_image else None,
    }


async def _set_tiles_image_to_sql_null(test_db_manager, tile_ids: list[str]) -> None:
    async with test_db_manager.async_session_factory() as session:
        await session.execute(
            update(TileSQLModel)
            .where(or_(*[_image_tile_condition(tile_id) for tile_id in tile_ids]))
            .values(image=null())
        )
        await session.commit()


async def _store_tile_image(test_db_manager, minio_s3, tile_id):
    contents = b"stored tile image"
    image = {
        "protocol": "s3",
        "server": minio_s3["server"],
        "bucket": minio_s3["bucket"],
        "key": f"tiles/{tile_id}.tif",
    }
    minio_s3["client"].put_object(image["bucket"], image["key"], io.BytesIO(contents), length=len(contents))
    async with test_db_manager.async_session_factory() as session:
        await session.execute(update(TileSQLModel).where(_image_tile_condition(tile_id)).values(image=image))
        await session.commit()
    return image


@pytest.fixture
async def stored_tile_image(test_db_manager, minio_s3, test_tile, test_acquisition):
    return await _store_tile_image(
        test_db_manager,
        minio_s3,
        format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake),
    )


async def test_tile_image_upload_roundtrip(async_client, test_db_manager, test_acquisition, test_tile, minio_s3):
    tile_id = str(format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake))
    await _set_tiles_image_to_sql_null(test_db_manager, [tile_id])
    path = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id}/image"
    location = {
        "protocol": "s3",
        "server": minio_s3["server"],
        "bucket": minio_s3["bucket"],
        "key": f"/tiles/{tile_id}.tif",
        "expiration": 600,
    }

    response = await async_client.post(path, json=location)

    assert response.status_code == 200, response.text
    presigned = response.json()
    assert presigned["key"] == f"tiles/{tile_id}.tif"
    assert presigned["expiration"] == 600
    async with httpx.AsyncClient() as storage:
        uploaded = await storage.put(presigned["url"], content=b"new tile image")
    assert uploaded.status_code == 200, uploaded.text
    tile_response = await async_client.get(path.removesuffix("/image"))
    assert tile_response.status_code == 200, tile_response.text
    assert tile_response.json()["image"] == {key: presigned[key] for key in ("protocol", "server", "bucket", "key")}

    response = await async_client.get(path, params={"expiration": 300})
    assert response.status_code == 200, response.text
    assert response.json()["expiration"] == 300
    async with httpx.AsyncClient() as storage:
        downloaded = await storage.get(response.json()["url"])
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.content == b"new tile image"


async def test_tile_image_download_uses_stored_location(async_client, test_acquisition, test_tile, stored_tile_image):
    tile_id = format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake)
    path = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id}/image"

    response = await async_client.get(path, params={"expiration": 300})

    assert response.status_code == 200, response.text
    presigned = response.json()
    assert {key: presigned[key] for key in stored_tile_image} == stored_tile_image
    assert presigned["expiration"] == 300
    async with httpx.AsyncClient() as storage:
        downloaded = await storage.get(presigned["url"])
    assert downloaded.status_code == 200, downloaded.text
    assert downloaded.content == b"stored tile image"


async def test_tile_image_delete_removes_object_and_clears_metadata(
    async_client, test_db_manager, test_acquisition, test_tile, stored_tile_image, minio_s3
):
    tile_id = format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake)
    path = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id}/image"

    response = await async_client.delete(path)

    assert response.status_code == 204, response.text
    assert response.content == b""
    with pytest.raises(S3Error) as error:
        minio_s3["client"].stat_object(stored_tile_image["bucket"], stored_tile_image["key"])
    assert error.value.code == "NoSuchKey"
    async with test_db_manager.async_session_factory() as session:
        tile = await session.scalar(
            select(TileSQLModel).where(
                and_(
                    TileSQLModel.dataset_id == test_tile.dataset_id,
                    TileSQLModel.run_id == test_tile.run_id,
                    TileSQLModel.row == test_tile.row,
                    TileSQLModel.col == test_tile.col,
                    TileSQLModel.retake == test_tile.retake,
                )
            )
        )
        assert tile is not None
        assert tile.image is None
    assert (await async_client.get(path)).status_code == 404


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
async def test_tile_image_rejects_another_acquisitions_tile(
    async_client, second_acquisition, test_tile, test_acquisition, method
):
    tile_id = format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake)
    path = f"/api/v2/acquisitions/{second_acquisition.acquisition_id}/tiles/{tile_id}/image"

    response = await async_client.request(method, path, json={"key": "/tile.tif"} if method == "POST" else None)

    assert response.status_code == 404, response.text


@pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
async def test_tile_image_missing_metadata_returns_error(
    async_client, test_db_manager, test_acquisition, test_tile, method
):
    tile_id = format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake)
    await _set_tiles_image_to_sql_null(test_db_manager, [tile_id])
    path = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id}/image"

    response = await async_client.request(method, path)

    assert response.status_code == (400 if method == "POST" else 404), response.text


@pytest.mark.parametrize("method", ["POST", "GET", "DELETE"])
@pytest.mark.parametrize("select_subset", [False, True])
async def test_tile_bulk_images_are_scoped_and_skip_missing_images(
    async_client,
    test_db_manager,
    test_acquisition,
    second_acquisition,
    minio_s3,
    method,
    select_subset,
):
    tile_ids = await _seed_image_tiles(async_client, test_acquisition.acquisition_id, 3)
    other_id = (await _seed_image_tiles(async_client, second_acquisition.acquisition_id, 1))[0]
    images = {
        tile_id: await _store_tile_image(test_db_manager, minio_s3, tile_id) for tile_id in [*tile_ids[:2], other_id]
    }
    await _set_tiles_image_to_sql_null(test_db_manager, [tile_ids[2]])
    selected = [tile_ids[0], tile_ids[2], other_id] if select_subset else None
    expected = tile_ids[:1] if select_subset else tile_ids[:2]
    path = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/images"

    response = await async_client.request(method, path, json=selected, params={"expiration": 300})

    assert response.status_code == 200, response.text
    result = response.json()
    assert set(result) == set(expected)
    if method == "DELETE":
        async with test_db_manager.async_session_factory() as session:
            tiles = {
                format_tile_id(
                    test_acquisition.montage_id
                    if tile.run_id == test_acquisition.run_id
                    else second_acquisition.montage_id,
                    tile.row,
                    tile.col,
                    tile.retake,
                ): tile
                for tile in (await session.scalars(select(TileSQLModel))).all()
            }
            assert set(tiles) == {*tile_ids, other_id}
            for tile_id in expected:
                assert tiles[tile_id].image is None
        for tile_id in expected:
            with pytest.raises(S3Error) as error:
                minio_s3["client"].stat_object(images[tile_id]["bucket"], images[tile_id]["key"])
            assert error.value.code == "NoSuchKey"
    else:
        for tile_id in expected:
            assert result[tile_id]["expiration"] == 300
            assert {key: result[tile_id][key] for key in images[tile_id]} == images[tile_id]
            async with httpx.AsyncClient() as storage:
                if method == "POST":
                    transfer = await storage.put(result[tile_id]["url"], content=b"replacement tile image")
                else:
                    transfer = await storage.get(result[tile_id]["url"])
                    assert transfer.content == b"stored tile image"
            assert transfer.status_code == 200, transfer.text
    untouched = [other_id] + (tile_ids[1:2] if select_subset else [])
    for tile_id in untouched:
        minio_s3["client"].stat_object(images[tile_id]["bucket"], images[tile_id]["key"])
        response = await async_client.get(
            f"/api/v2/acquisitions/"
            f"{second_acquisition.acquisition_id if tile_id == other_id else test_acquisition.acquisition_id}"
            f"/tiles/{tile_id}"
        )
        assert response.status_code == 200, response.text
        assert response.json()["image"] == images[tile_id]


@pytest.mark.parametrize("method", ["POST", "GET", "DELETE"])
@pytest.mark.parametrize("select_subset", [False, True])
@pytest.mark.parametrize("failure", [None, "gcs", "storage"])
async def test_bulk_tile_images_multiple_servers_and_errors(
    async_client, test_db_manager, test_acquisition, monkeypatch, caplog, method, select_subset, failure
):
    tile_ids = await _seed_image_tiles(async_client, test_acquisition.acquisition_id, 4)
    images = {
        tile_id: {
            **_tile_image(f"tiles/{index}.tif"),
            "server": f"http://storage-{index % 2}.example.com",
            "protocol": "gcs" if failure == "gcs" and index == 1 else "s3",
        }
        for index, tile_id in enumerate(tile_ids)
    }
    async with test_db_manager.async_session_factory() as session:
        for tile_id, image in images.items():
            await session.execute(update(TileSQLModel).where(_image_tile_condition(tile_id)).values(image=image))
        await session.commit()
    clients = {image["server"]: Mock() for image in images.values()}
    failed_id = tile_ids[1]

    def presign(server, operation, Params, ExpiresIn):
        if failure == "storage" and Params["Key"] == images[failed_id]["key"]:
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "presign denied"}}, operation)
        return f"{server}/{Params['Key']}?operation={operation}&expiration={ExpiresIn}"

    def delete_object(Bucket, Key):
        if failure == "storage" and Key == images[failed_id]["key"]:
            raise ClientError({"Error": {"Code": "AccessDenied", "Message": "delete denied"}}, "DeleteObject")

    for server, client in clients.items():
        client.generate_presigned_url.side_effect = lambda operation, Params, ExpiresIn, server=server: presign(
            server, operation, Params, ExpiresIn
        )
        client.delete_object.side_effect = delete_object
    factory = Mock(side_effect=lambda service, endpoint_url: clients[endpoint_url])
    monkeypatch.setattr("boto3.client", factory)
    selected = tile_ids[:3] if select_subset else None
    requested = tile_ids[:3] if select_subset else tile_ids

    response = await async_client.request(
        method,
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/images",
        json=selected,
        params={"expiration": 300},
    )

    assert response.status_code == 200, response.text
    async with test_db_manager.async_session_factory() as session:
        stored = {
            format_tile_id(
                test_acquisition.montage_id
                if tile.run_id == test_acquisition.run_id
                else second_acquisition.montage_id,
                tile.row,
                tile.col,
                tile.retake,
            ): tile.image
            for tile in (await session.scalars(select(TileSQLModel))).all()
        }
    expected = set(requested) - ({failed_id} if failure is not None else set())
    assert set(response.json()) == expected
    assert {call.kwargs["endpoint_url"] for call in factory.call_args_list} == {
        images[tile_id]["server"] for tile_id in requested if images[tile_id]["protocol"] == "s3"
    }
    if failure == "storage":
        assert ("delete denied" if method == "DELETE" else "presign denied") in caplog.text
    elif failure == "gcs":
        assert "not implemented" in caplog.text
    for tile_id, image in images.items():
        assert stored[tile_id] == (None if method == "DELETE" and tile_id in expected else image)
    operation = "delete_object" if method == "DELETE" else "generate_presigned_url"
    for server, client in clients.items():
        calls = getattr(client, operation).call_args_list
        expected_keys = {
            images[tile_id]["key"]
            for tile_id in requested
            if images[tile_id]["server"] == server and images[tile_id]["protocol"] == "s3"
        }
        actual_keys = {call.kwargs["Key"] if method == "DELETE" else call.kwargs["Params"]["Key"] for call in calls}
        assert actual_keys == expected_keys
        assert len(calls) == len(expected_keys)
    if method != "DELETE":
        for tile_id in expected:
            result = response.json()[tile_id]
            assert result["server"] == images[tile_id]["server"]
            assert result["expiration"] == 300
            assert result["url"] == (
                f"{images[tile_id]['server']}/{images[tile_id]['key']}"
                f"?operation={'put_object' if method == 'POST' else 'get_object'}&expiration=300"
            )


@pytest.mark.parametrize("operation", ["bulk", "all", "single"])
async def test_tile_deletion_preserves_tiles_with_images(
    async_client, test_db_manager, test_acquisition, test_tile, operation
):
    base = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles"
    path = (
        f"{base}/{format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake)}"
        if operation == "single"
        else f"{base}/{operation}"
    )

    response = await async_client.request(
        "DELETE",
        path,
        json=[str(format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake))]
        if operation == "bulk"
        else None,
    )

    if operation == "single":
        assert response.status_code == 404, response.text
    else:
        assert response.status_code == 200, response.text
        assert response.json()["deleted"] == 0
        if operation == "bulk":
            assert response.json()["not_found"] == [
                str(format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake))
            ]
    async with test_db_manager.async_session_factory() as session:
        tile = await session.scalar(
            select(TileSQLModel).where(
                and_(
                    TileSQLModel.dataset_id == test_tile.dataset_id,
                    TileSQLModel.run_id == test_tile.run_id,
                    TileSQLModel.row == test_tile.row,
                    TileSQLModel.col == test_tile.col,
                    TileSQLModel.retake == test_tile.retake,
                )
            )
        )
        assert tile is not None
        assert tile.image == test_tile.image


async def _seed_image_tiles(
    async_client: AsyncClient,
    acquisition_id: str,
    count: int,
    *,
    image_is_sql_null: bool = False,
    test_db_manager=None,
) -> list[str]:
    tiles = [_image_tile_payload(f"tile_{i}", i, include_image=not image_is_sql_null) for i in range(count)]
    response = await async_client.post(f"/api/v2/acquisitions/{acquisition_id}/tiles/bulk", json=tiles)
    assert response.status_code in (200, 201), response.text
    acquisition = (await async_client.get(f"/api/v2/acquisitions/{acquisition_id}")).json()
    tile_ids = [format_tile_id(acquisition["montage_id"], 0, i, 0) for i in range(count)]
    if image_is_sql_null:
        assert test_db_manager is not None
        await _set_tiles_image_to_sql_null(test_db_manager, tile_ids)
    return tile_ids
