import pytest


@pytest.mark.asyncio
async def test_list_acquisitions(async_client):
    response = await async_client.get("/api/v2/acquisitions")
    assert response.status_code == 200
    assert "acquisitions" in response.json()
    assert "metadata" in response.json()


@pytest.mark.asyncio
async def test_create_acquisition(async_client, test_roi, test_acquisition_task):
    acquisition_data = {
        "acquisition_id": "TEST_ACQ_CREATE",
        "montage_id": "TEST_MONTAGE_CREATE",
        "roi_id": test_roi.roi_id,
        "acquisition_task_id": test_acquisition_task.task_id,
        "hardware_settings": {
            "scope_id": "TEST_SCOPE",
            "camera_model": "Test Camera",
            "camera_serial": "12345",
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
        "tilt_angle": 0.0,
        "lens_correction": False,
        "status": "imaging",
    }
    response = await async_client.post("/api/v2/acquisitions", json=acquisition_data)
    assert response.status_code == 200
    assert response.json()["acquisition_id"] == "TEST_ACQ_CREATE"


@pytest.mark.asyncio
async def test_get_acquisition(async_client, test_acquisition):
    response = await async_client.get(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}"
    )
    assert response.status_code == 200
    assert response.json()["acquisition_id"] == test_acquisition.acquisition_id


@pytest.mark.asyncio
async def test_update_acquisition(async_client, test_acquisition):
    update_data = {"status": "acquired"}
    response = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}", json=update_data
    )
    assert response.status_code == 200
    assert response.json()["status"] == "acquired"


@pytest.mark.asyncio
async def test_delete_acquisition(async_client, test_roi, test_acquisition_task):
    acquisition_data = {
        "acquisition_id": "TEST_ACQ_DELETE",
        "montage_id": "TEST_MONTAGE_DELETE",
        "roi_id": test_roi.roi_id,
        "acquisition_task_id": test_acquisition_task.task_id,
        "hardware_settings": {
            "scope_id": "TEST_SCOPE",
            "camera_model": "Test Camera",
            "camera_serial": "12345",
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
        "tilt_angle": 0.0,
        "lens_correction": False,
        "status": "imaging",
    }
    create_response = await async_client.post(
        "/api/v2/acquisitions", json=acquisition_data
    )
    assert create_response.status_code == 200

    response = await async_client.delete(f"/api/v2/acquisitions/TEST_ACQ_DELETE")
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_add_tile_to_acquisition(async_client, test_acquisition):
    tile_data = {
        "tile_id": "TEST_TILE_ADD",
        "raster_index": 2,
        "stage_position": {"x": 150, "y": 250},
        "raster_position": {"row": 1, "col": 1},
        "focus_score": 0.92,
        "min_value": 5,
        "max_value": 250,
        "mean_value": 120,
        "std_value": 30,
        "image_path": "/path/to/test/tile_add.tif",
    }
    response = await async_client.post(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles", json=tile_data
    )
    assert response.status_code == 200
    assert response.json()["tile_id"] == "TEST_TILE_ADD"


@pytest.mark.asyncio
async def test_get_tile_from_acquisition(async_client, test_acquisition):
    # First, add a tile to the acquisition
    tile_data = {
        "tile_id": "TEST_TILE_ADD",
        "raster_index": 2,
        "stage_position": {"x": 150, "y": 250},
        "raster_position": {"row": 1, "col": 1},
        "focus_score": 0.92,
        "min_value": 5,
        "max_value": 250,
        "mean_value": 120,
        "std_value": 30,
        "image_path": "/path/to/test/tile_add.tif",
    }
    add_response = await async_client.post(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles", json=tile_data
    )
    assert add_response.status_code == 200

    # Then try to retrieve the tile
    response = await async_client.get(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/TEST_TILE_ADD"
    )
    assert response.status_code == 200
