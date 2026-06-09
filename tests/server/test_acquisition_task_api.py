from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from temdb.models import AcquisitionStatus
from temdb.server.documents import (
    AcquisitionDocument,
    AcquisitionTaskDocument,
    ROIDocument,
    SectionDocument,
)


@pytest.mark.asyncio
async def test_list_acquisition_tasks_unfiltered(async_client: AsyncClient):
    """Test retrieving a list of all acquisition tasks."""
    response = await async_client.get("/api/v2/acquisition-tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_acquisition_tasks_filtered(
    async_client: AsyncClient,
    test_specimen,
    test_block,
    test_roi,
    test_roi2,
    test_acquisition_task,
    test_acquisition_task2,
):
    """Test filtering acquisition tasks."""

    response_roi = await async_client.get(f"/api/v2/acquisition-tasks?roi_id={test_roi.roi_id}")

    assert response_roi.status_code == 200
    res_roi_data = response_roi.json()
    assert isinstance(res_roi_data, list)

    assert len(res_roi_data) >= 1, (
        f"API call returned empty list, expected at least one task matching roi_id {test_roi.roi_id}"
    )

    assert all(task["roi_ref"]["id"] == str(test_roi.id) for task in res_roi_data)
    assert any(task["task_id"] == test_acquisition_task.task_id for task in res_roi_data)

    response_block = await async_client.get(f"/api/v2/acquisition-tasks?block_id={test_block.block_id}")
    assert response_block.status_code == 200
    res_block_data = response_block.json()
    assert isinstance(res_block_data, list)
    assert len(res_block_data) >= 1
    assert all(task["block_ref"]["id"] == str(test_block.id) for task in res_block_data)

    response_spec = await async_client.get(f"/api/v2/acquisition-tasks?specimen_id={test_specimen.specimen_id}")
    assert response_spec.status_code == 200
    res_spec_data = response_spec.json()
    assert isinstance(res_spec_data, list)
    assert len(res_spec_data) >= 1
    assert all(task["specimen_ref"]["id"] == str(test_specimen.id) for task in res_spec_data)


@pytest.mark.asyncio
async def test_list_acquisition_tasks_skip_destroyed(
    async_client: AsyncClient,
    test_specimen,
    test_block,
    test_cutting_session,
    test_substrate,
    test_acquisition_task,
):
    destroyed_section = SectionDocument(
        section_id="TEST_SECTION_DESTROYED_001",
        section_number=2,
        timestamp=datetime.now(timezone.utc),
        cutting_session_id=test_cutting_session.cutting_session_id,
        block_id=test_block.block_id,
        specimen_id=test_specimen.specimen_id,
        cutting_session_ref=test_cutting_session.id,
        substrate_ref=test_substrate.id,
        destroyed=True,
        media_id="TEST_MEDIA_001",
    )
    await destroyed_section.insert()

    destroyed_roi = ROIDocument(
        roi_id="SPEC001.BLK001.CS001.SEC002.SUB001.ROI001",
        roi_number=1,
        section_id=destroyed_section.section_id,
        block_id=test_block.block_id,
        specimen_id=test_specimen.specimen_id,
        substrate_media_id="SUB001",
        hierarchy_level=1,
        section_ref=destroyed_section.id,
        parent_roi_ref=None,
        updated_at=datetime.now(timezone.utc),
        section_number=destroyed_section.section_number,
    )
    await destroyed_roi.insert()

    destroyed_task = AcquisitionTaskDocument(
        task_id="TEST_TASK_DESTROYED_001",
        specimen_id=test_specimen.specimen_id,
        block_id=test_block.block_id,
        roi_id=destroyed_roi.roi_id,
        specimen_ref=test_specimen.id,
        block_ref=test_block.id,
        roi_ref=destroyed_roi.id,
        task_type="standard_acquisition",
        version=1,
        created_at=datetime.now(timezone.utc),
    )
    await destroyed_task.insert()

    default_response = await async_client.get("/api/v2/acquisition-tasks")
    assert default_response.status_code == 200
    default_ids = {task["task_id"] for task in default_response.json()}
    assert test_acquisition_task.task_id in default_ids
    assert destroyed_task.task_id not in default_ids

    include_response = await async_client.get("/api/v2/acquisition-tasks?skip_destroyed=false")
    assert include_response.status_code == 200
    include_ids = {task["task_id"] for task in include_response.json()}
    assert destroyed_task.task_id in include_ids


@pytest.mark.asyncio
async def test_list_acquisition_tasks_skip_completed(
    async_client: AsyncClient,
    test_specimen,
    test_block,
    test_roi,
    test_acquisition_task,
    test_roi2,
):
    failed_acquisition = AcquisitionDocument(
        acquisition_id="TEST_ACQ_QC_PENDING_001",
        montage_id="TEST_MONTAGE_QC_PENDING_001",
        specimen_id=test_specimen.specimen_id,
        roi_id=test_roi.roi_id,
        acquisition_task_id=test_acquisition_task.task_id,
        specimen_ref=test_specimen.id,
        roi_ref=test_roi.id,
        acquisition_task_ref=test_acquisition_task.id,
        hardware_settings={
            "scope_id": "TEST_SCOPE_001",
            "camera_model": "Test Camera",
            "camera_serial": "12345",
            "camera_bit_depth": 16,
            "media_type": "tape",
        },
        acquisition_settings={
            "magnification": 1000,
            "spot_size": 2,
            "exposure_time": 100,
            "tile_size": [4096, 4096],
            "tile_overlap": 0.1,
            "saved_bit_depth": 8,
        },
        status=AcquisitionStatus.QC_FAILED,
        start_time=datetime.now(timezone.utc),
    )
    passed_acquisition = AcquisitionDocument(
        acquisition_id="TEST_ACQ_QC_PASSED_001",
        montage_id="TEST_MONTAGE_QC_PASSED_001",
        specimen_id=test_specimen.specimen_id,
        roi_id=test_roi.roi_id,
        acquisition_task_id=test_acquisition_task.task_id,
        specimen_ref=test_specimen.id,
        roi_ref=test_roi.id,
        acquisition_task_ref=test_acquisition_task.id,
        hardware_settings={
            "scope_id": "TEST_SCOPE_001",
            "camera_model": "Test Camera",
            "camera_serial": "12345",
            "camera_bit_depth": 16,
            "media_type": "tape",
        },
        acquisition_settings={
            "magnification": 1000,
            "spot_size": 2,
            "exposure_time": 100,
            "tile_size": [4096, 4096],
            "tile_overlap": 0.1,
            "saved_bit_depth": 8,
        },
        status=AcquisitionStatus.QC_PASSED,
        start_time=datetime.now(timezone.utc),
    )
    await failed_acquisition.insert()
    await passed_acquisition.insert()

    default_response = await async_client.get("/api/v2/acquisition-tasks")
    assert default_response.status_code == 200
    default_ids = {task["task_id"] for task in default_response.json()}
    assert test_acquisition_task.task_id not in default_ids

    include_response = await async_client.get("/api/v2/acquisition-tasks?skip_completed=false")
    assert include_response.status_code == 200
    include_ids = {task["task_id"] for task in include_response.json()}
    assert test_acquisition_task.task_id in include_ids

    response_media = await async_client.get(f"/api/v2/acquisition-tasks?media_id={test_roi2.substrate_media_id}")
    assert response_media.status_code == 200
    res_media_data = response_media.json()
    assert isinstance(res_media_data, list)
    assert len(res_media_data) >= 1
    assert all(task["roi_ref"]["substrate_media_id"] == test_roi2.substrate_media_id for task in res_media_data)


@pytest.mark.asyncio
async def test_create_acquisition_task(async_client: AsyncClient, test_specimen, test_block, test_roi):
    """Test creating a new acquisition task successfully."""
    task_id_hr = f"TASK_CREATE_{int(datetime.now(timezone.utc).timestamp())}"
    task_data = {
        "task_id": task_id_hr,
        "specimen_id": test_specimen.specimen_id,
        "block_id": test_block.block_id,
        "roi_id": test_roi.roi_id,
        "tags": ["test", "create"],
        "metadata": {"test_key": "test_value"},
        "task_type": "standard_acquisition",
    }
    response = await async_client.post("/api/v2/acquisition-tasks", json=task_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["task_id"] == task_id_hr
    assert response_data["specimen_ref"]["id"] == str(test_specimen.id)
    assert response_data["block_ref"]["id"] == str(test_block.id)
    assert response_data["roi_ref"]["id"] == str(test_roi.id)

    # await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_hr}")


@pytest.mark.asyncio
async def test_create_acquisition_task_invalid_parent(async_client: AsyncClient, test_specimen, test_block):
    """Test creating a task fails atomically if a parent doesn't exist (transaction test)."""
    task_id_hr = f"TASK_CREATE_INVALID_{int(datetime.now(timezone.utc).timestamp())}"
    invalid_roi_id = "SPEC999.BLK999.CS999.SEC999.SUB999.ROI9999999"
    task_data = {
        "task_id": task_id_hr,
        "specimen_id": test_specimen.specimen_id,
        "block_id": test_block.block_id,
        "roi_id": invalid_roi_id,
    }
    response = await async_client.post("/api/v2/acquisition-tasks", json=task_data)
    assert response.status_code == 404
    assert f"ROI '{invalid_roi_id}' not found" in response.json()["detail"]

    get_response = await async_client.get(f"/api/v2/acquisition-tasks/{task_id_hr}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_acquisition_task(async_client: AsyncClient, test_acquisition_task):
    """Test retrieving a specific acquisition task."""
    response = await async_client.get(f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["task_id"] == test_acquisition_task.task_id
    assert response_data["_id"] == str(test_acquisition_task.id)
    assert response_data["specimen_ref"]["id"] == str(test_acquisition_task.specimen_ref.ref.id)
    assert response_data["block_ref"]["id"] == str(test_acquisition_task.block_ref.ref.id)
    assert response_data["roi_ref"]["id"] == str(test_acquisition_task.roi_ref.ref.id)


@pytest.mark.asyncio
async def test_get_acquisition_task_not_found(async_client: AsyncClient):
    """Test retrieving a non-existent task."""
    response = await async_client.get("/api/v2/acquisition-tasks/NON_EXISTENT_TASK")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_acquisition_task(async_client: AsyncClient, test_acquisition_task):
    """Test updating a task's metadata."""
    update_data = {
        "metadata": {"updated_key": "updated_value"},
    }
    response = await async_client.patch(f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}", json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["metadata"]["updated_key"] == "updated_value"
    assert response_data["task_id"] == test_acquisition_task.task_id
    assert "updated_at" in response_data
    assert response_data["updated_at"] is not None


@pytest.mark.asyncio
async def test_delete_task(async_client: AsyncClient, test_specimen, test_block, test_roi):
    """Test deleting a task successfully (when it has no dependencies)."""
    task_id_hr = f"TASK_DELETE_{int(datetime.now(timezone.utc).timestamp())}"
    task_data = {
        "task_id": task_id_hr,
        "specimen_id": test_specimen.specimen_id,
        "block_id": test_block.block_id,
        "roi_id": test_roi.roi_id,
    }
    create_response = await async_client.post("/api/v2/acquisition-tasks", json=task_data)
    assert create_response.status_code == 201

    # Delete the task
    delete_response = await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_hr}")
    assert delete_response.status_code == 204

    # Verify it's gone
    get_response = await async_client.get(f"/api/v2/acquisition-tasks/{task_id_hr}")
    assert get_response.status_code == 404


# @pytest.mark.asyncio
# async def test_delete_task_with_acquisitions(async_client: AsyncClient, test_acquisition_task, test_acquisition):
#     """Test deleting a task fails if it has associated Acquisitions."""
#     # test_acquisition fixture links to test_acquisition_task
#     response = await async_client.delete(f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}")
#     assert response.status_code == 400
#     assert "associated Acquisitions" in response.json()["detail"].lower() # Check message

# @pytest.mark.asyncio
# async def test_get_task_acquisitions(async_client: AsyncClient, test_acquisition_task, test_acquisition):
#      """Test retrieving acquisitions associated with a task."""
#      # test_acquisition fixture links to test_acquisition_task
#      response = await async_client.get(f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}/acquisitions")
#      assert response.status_code == 200
#      response_data = response.json()
#      assert isinstance(response_data, list)
#      assert len(response_data) >= 1
#      assert any(acq["acquisition_id"] == test_acquisition.acquisition_id for acq in response_data)
#      assert all(acq["acquisition_task_ref"]["$id"] == str(test_acquisition_task.id) for acq in response_data)


@pytest.mark.asyncio
async def test_create_tasks_batch(async_client: AsyncClient, test_specimen, test_block, test_roi):
    """Test creating multiple tasks in a batch."""
    task_id_1 = f"TASK_BATCH_1_{int(datetime.now(timezone.utc).timestamp())}"
    task_id_2 = f"TASK_BATCH_2_{int(datetime.now(timezone.utc).timestamp())}"
    tasks_data = [
        {
            "task_id": task_id_1,
            "specimen_id": test_specimen.specimen_id,
            "block_id": test_block.block_id,
            "roi_id": test_roi.roi_id,
            "tags": ["batch1"],
        },
        {
            "task_id": task_id_2,
            "specimen_id": test_specimen.specimen_id,
            "block_id": test_block.block_id,
            "roi_id": test_roi.roi_id,
            "tags": ["batch2"],
            "task_type": "alignment_task",
        },
    ]
    response = await async_client.post("/api/v2/acquisition-tasks/batch", json=tasks_data)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2
    assert response_data[0]["task_id"] == task_id_1
    assert response_data[1]["task_id"] == task_id_2
    assert response_data[1]["task_type"] == "alignment_task"
    assert response_data[0]["roi_ref"]["id"] == str(test_roi.id)
    assert response_data[1]["roi_ref"]["id"] == str(test_roi.id)

    # await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_1}")
    # await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_2}")


@pytest.mark.asyncio
async def test_create_tasks_batch_partial_success(async_client: AsyncClient, test_specimen, test_block, test_roi):
    """Test that batch creation fails at the invalid task but keeps valid ones."""
    task_id_1 = f"TASK_BATCH_PART_1_{int(datetime.now(timezone.utc).timestamp())}"
    task_id_2 = f"TASK_BATCH_PART_2_{int(datetime.now(timezone.utc).timestamp())}"
    invalid_roi_id = "SPEC999.BLK999.CS999.SEC999.SUB999.ROI9999998"
    tasks_data = [
        {  # Valid task
            "task_id": task_id_1,
            "specimen_id": test_specimen.specimen_id,
            "block_id": test_block.block_id,
            "roi_id": test_roi.roi_id,
        },
        {  # Invalid task (bad ROI ID)
            "task_id": task_id_2,
            "specimen_id": test_specimen.specimen_id,
            "block_id": test_block.block_id,
            "roi_id": invalid_roi_id,
        },
    ]
    response = await async_client.post("/api/v2/acquisition-tasks/batch", json=tasks_data)
    assert response.status_code == 404
    assert f"ROI '{invalid_roi_id}' not found" in response.json()["detail"]

    get_resp_1 = await async_client.get(f"/api/v2/acquisition-tasks/{task_id_1}")
    assert get_resp_1.status_code == 200
    assert get_resp_1.json()["task_id"] == task_id_1

    get_resp_2 = await async_client.get(f"/api/v2/acquisition-tasks/{task_id_2}")
    assert get_resp_2.status_code == 404

    delete_resp = await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_1}")
    assert delete_resp.status_code == 204
