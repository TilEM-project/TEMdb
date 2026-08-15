from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from temdb.server.config import config
from temdb.server.ids import uuid7

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

    # Filter by status: the seeded acquisition is in flight (status NULL)
    resp_status = await async_client.get("/api/v2/acquisitions?status=in_flight")
    assert resp_status.status_code == 200
    assert all(a["status"] is None for a in resp_status.json()["acquisitions"])
    assert any(a["acquisition_id"] == test_acquisition.acquisition_id for a in resp_status.json()["acquisitions"])


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
        "microscope_id": str(test_microscope.microscope_id),
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
        "microscope_id": str(test_microscope.microscope_id),
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
async def test_delete_acquisition(async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope):
    """Test deleting an acquisition successfully (when it has no Tiles)."""
    acq_id_hr = f"ACQ_DELETE_{int(datetime.now(timezone.utc).timestamp())}"
    acq_data = {
        "acquisition_id": acq_id_hr,
        "montage_id": "MONTAGE_DELETE",
        "roi_id": test_roi.roi_id,
        "acquisition_task_id": test_acquisition_task.task_id,
        "microscope_id": str(test_microscope.microscope_id),
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
    tile_id_hr = str(uuid7())
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
        tile_id_hr = str(uuid7())
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
        assert data1["tiles"][0]["tile_id"] == str(test_tile.tile_id)
        assert data1["tiles"][0]["acquisition_id"] == acq_id

        assert next_cursor == test_tile.raster_index

    if next_cursor is not None:
        response2 = await async_client.get(f"/api/v2/acquisitions/{acq_id}/tiles?limit=1&cursor={next_cursor}")
        assert response2.status_code == 200
        data2 = response2.json()
        assert len(data2["tiles"]) <= 1


@pytest.mark.asyncio
async def test_get_tiles_from_acquisition_bbox_filter(async_client: AsyncClient, test_acquisition):
    acq_id = test_acquisition.acquisition_id
    tile_specs = [
        (str(uuid7()), 10, 10.0, 10.0),
        (str(uuid7()), 11, 25.0, 20.0),
        (str(uuid7()), 12, 40.0, 30.0),
    ]
    for tile_id, raster_index, x, y in tile_specs:
        response = await async_client.post(
            f"/api/v2/acquisitions/{acq_id}/tiles",
            json={
                "tile_id": tile_id,
                "raster_index": raster_index,
                "stage_position": {"x": x, "y": y},
                "raster_position": {"row": 0, "col": raster_index},
                "focus_score": 0.9,
                "min_value": 0,
                "max_value": 255,
                "mean_value": 128,
                "std_value": 25,
                "image_path": f"/path/to/{tile_id}.tif",
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
async def test_get_tile_from_acquisition(async_client: AsyncClient, test_acquisition, test_tile):
    """Test retrieving a specific tile from an acquisition."""
    response = await async_client.get(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/{test_tile.tile_id}"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["tile_id"] == str(test_tile.tile_id)
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
    tile_id_hr = str(uuid7())
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
    import json

    num_tiles = 100
    tiles_data = []
    for i in range(num_tiles):
        tile_id_hr = str(uuid7())
        tiles_data.append(
            {
                "tile_id": tile_id_hr,
                "raster_index": i + 1000,
                "stage_position": {"x": float(i), "y": float(i + 1)},
                "raster_position": {"row": i // 10, "col": i % 10},
                "focus_score": 0.8,
                "min_value": 10,
                "max_value": 240,
                "mean_value": 100,
                "std_value": 20,
                "image_path": f"/path/to/gzip/{tile_id_hr}.tif",
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
            "microscope_id": str(test_microscope.microscope_id),
            "dataset_id": ds["dataset_id"],
            "hardware_settings": {
                "scope_id": "S1",
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

    tile_id = str(uuid7())
    add = await async_client.post(
        "/api/v2/acquisitions/ACQ_E2E_001/tiles",
        json={
            "tile_id": tile_id,
            "raster_index": 7,
            "stage_position": {"x": 11.5, "y": 22.5},
            "raster_position": {"row": 0, "col": 7},
            "focus_score": 0.9,
            "min_value": 0,
            "max_value": 255,
            "mean_value": 128,
            "std_value": 25,
            "image_path": "/p/7.tif",
        },
    )
    assert add.status_code == 201  # would 409 if dataset_id were not persisted

    got = (await async_client.get(f"/api/v2/acquisitions/ACQ_E2E_001/tiles/{tile_id}")).json()
    assert got["stage_position"] == {"x": 11.5, "y": 22.5}
    assert got["raster_position"] == {"row": 0, "col": 7}
