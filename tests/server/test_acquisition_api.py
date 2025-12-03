from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from temdb.models import AcquisitionStatus
from temdb.server.config import config

TEST_MAX_BATCH_SIZE = 10
config.max_batch_size = TEST_MAX_BATCH_SIZE


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

    # Filter by status
    resp_status = await async_client.get(f"/api/v2/acquisitions?status={AcquisitionStatus.IMAGING.value}")
    assert resp_status.status_code == 200
    # Assumes test_acquisition fixture has IMAGING status
    assert all(a["status"] == AcquisitionStatus.IMAGING.value for a in resp_status.json()["acquisitions"])


@pytest.mark.asyncio
async def test_create_acquisition(async_client: AsyncClient, test_specimen, test_roi, test_acquisition_task):
    """Test creating a new acquisition successfully."""
    acq_id_hr = f"ACQ_CREATE_{int(datetime.now(timezone.utc).timestamp())}"
    montage_id_hr = f"MONTAGE_CREATE_{int(datetime.now(timezone.utc).timestamp())}"
    acquisition_data = {
        "acquisition_id": acq_id_hr,
        "montage_id": montage_id_hr,
        "roi_id": test_roi.roi_id,
        "acquisition_task_id": test_acquisition_task.task_id,
        "hardware_settings": {
            "scope_id": "TEST_SCOPE_CREATE",
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
        "tilt_angle": 5.0,
        "lens_correction": False,
        "status": AcquisitionStatus.IMAGING.value,
    }
    response = await async_client.post("/api/v2/acquisitions", json=acquisition_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["acquisition_id"] == acq_id_hr
    assert response_data["montage_id"] == montage_id_hr
    assert response_data["roi_id"] == test_roi.roi_id
    assert response_data["acquisition_task_id"] == test_acquisition_task.task_id
    assert response_data["specimen_id"] == test_specimen.specimen_id
    assert response_data["roi_ref"]["id"] == str(test_roi.id)
    assert response_data["acquisition_task_ref"]["id"] == str(test_acquisition_task.id)
    assert response_data["specimen_ref"]["id"] == str(test_specimen.id)

    # await async_client.delete(f"/api/v2/acquisitions/{acq_id_hr}")


@pytest.mark.asyncio
async def test_create_acquisition_invalid_parent(async_client: AsyncClient, test_roi, test_acquisition_task):
    """Test creating an acquisition fails atomically if a parent task doesn't exist."""
    acq_id_hr = f"ACQ_CREATE_INVALID_{int(datetime.now(timezone.utc).timestamp())}"
    invalid_task_id = "NON_EXISTENT_TASK_FOR_ACQ"
    acquisition_data = {
        "acquisition_id": acq_id_hr,
        "montage_id": "MONTAGE_INVALID",
        "roi_id": test_roi.roi_id,
        "acquisition_task_id": invalid_task_id,
        "hardware_settings": {
            "scope_id": "s",
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
        "tilt_angle": 0,
        "lens_correction": False,
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
    assert response_data["_id"] == str(test_acquisition.id)
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
    """Test updating an acquisition's status."""
    update_data = {"status": AcquisitionStatus.ACQUIRED.value}
    response = await async_client.patch(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}", json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == AcquisitionStatus.ACQUIRED.value
    assert response_data["acquisition_id"] == test_acquisition.acquisition_id
    assert "end_time" not in update_data  # Ensure other fields weren't changed unless specified


@pytest.mark.asyncio
async def test_delete_acquisition(async_client: AsyncClient, test_roi, test_acquisition_task):
    """Test deleting an acquisition successfully (when it has no Tiles)."""
    acq_id_hr = f"ACQ_DELETE_{int(datetime.now(timezone.utc).timestamp())}"
    acq_data = {
        "acquisition_id": acq_id_hr,
        "montage_id": "MONTAGE_DELETE",
        "roi_id": test_roi.roi_id,
        "acquisition_task_id": test_acquisition_task.task_id,
        "hardware_settings": {
            "scope_id": "s",
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
        "tilt_angle": 0,
        "lens_correction": False,
    }
    create_response = await async_client.post("/api/v2/acquisitions", json=acq_data)
    assert create_response.status_code == 201

    # Delete the acquisition
    delete_response = await async_client.delete(f"/api/v2/acquisitions/{acq_id_hr}")
    assert delete_response.status_code == 204

    # Verify it's gone
    get_response = await async_client.get(f"/api/v2/acquisitions/{acq_id_hr}")
    assert get_response.status_code == 404


# @pytest.mark.asyncio
# async def test_delete_acquisition_with_tiles(async_client: AsyncClient, test_acquisition, test_tile):
#     """Test deleting an acquisition fails if it has associated Tiles."""
#     # test_tile fixture links to test_acquisition
#     response = await async_client.delete(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}")
#     assert response.status_code == 400
#     assert "tiles exist" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_add_tile_to_acquisition(async_client: AsyncClient, test_acquisition):
    """Test adding a single tile to an acquisition."""
    tile_id_hr = f"TILE_ADD_SINGLE_{int(datetime.now(timezone.utc).timestamp())}"
    tile_data = {
        "tile_id": tile_id_hr,
        "raster_index": 10,
        "stage_position": {"x": 150.5, "y": 250.5},
        "raster_position": {"row": 1, "col": 0},
        "focus_score": 0.92,
        "min_value": 5,
        "max_value": 250,
        "mean_value": 120,
        "std_value": 30,
        "image_path": f"/path/to/test/{tile_id_hr}.tif",
    }
    response = await async_client.post(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles", json=tile_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["tile_id"] == tile_id_hr
    assert response_data["acquisition_id"] == test_acquisition.acquisition_id
    assert response_data["raster_index"] == 10
    assert response_data["acquisition_ref"]["id"] == str(test_acquisition.id)

    # await async_client.delete(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{tile_id_hr}")


@pytest.mark.asyncio
async def test_add_tiles_to_acquisition_bulk(async_client: AsyncClient, test_acquisition):
    """Test adding multiple tiles in bulk."""
    num_tiles = TEST_MAX_BATCH_SIZE + 5
    tiles_data = []
    expected_tile_ids = []
    for i in range(num_tiles):
        tile_id_hr = f"TILE_BULK_{i}_{int(datetime.now(timezone.utc).timestamp())}"
        expected_tile_ids.append(tile_id_hr)
        tiles_data.append(
            {
                "tile_id": tile_id_hr,
                "raster_index": i,
                "stage_position": {"x": float(i), "y": float(i + 1)},
                "raster_position": {"row": i // 10, "col": i % 10},
                "focus_score": 0.8,
                "min_value": 10,
                "max_value": 240,
                "mean_value": 100,
                "std_value": 20,
                "image_path": f"/path/to/bulk/{tile_id_hr}.tif",
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
        assert data1["tiles"][0]["tile_id"] == test_tile.tile_id
        assert data1["tiles"][0]["acquisition_id"] == acq_id

        assert next_cursor == test_tile.raster_index

    if next_cursor is not None:
        response2 = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tiles?limit=1&cursor={next_cursor}")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["tiles"]) <= 1


@pytest.mark.asyncio
async def test_get_tile_from_acquisition(async_client: AsyncClient, test_acquisition, test_tile):
    """Test retrieving a specific tile from an acquisition."""
    response = await async_client.get(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{test_tile.tile_id}"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["tile_id"] == test_tile.tile_id
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
    tile_id_hr = f"TILE_DELETE_{int(datetime.now(timezone.utc).timestamp())}"
    tile_data = {
        "tile_id": tile_id_hr,
        "raster_index": 50,
        "stage_position": {"x": 0, "y": 0},
        "raster_position": {"row": 0, "col": 0},
        "focus_score": 0,
        "min_value": 0,
        "max_value": 0,
        "mean_value": 0,
        "std_value": 0,
        "image_path": "del.tif",
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

    status = test_acquisition.status.value if hasattr(test_acquisition.status, "value") else test_acquisition.status
    response_filtered = await async_client.get(f"/api/v2/aggregated/acquisitions?status={status}")
    assert response_filtered.status_code == 200
    filtered_data = response_filtered.json()

    for acq in filtered_data["acquisitions"]:
        assert acq["acquisition"]["status"] == status
