import pytest
from httpx import AsyncClient
from datetime import datetime, timezone


from temdb.models.v2.enum_schemas import AcquisitionTaskStatus
from temdb.models.v2.task import AcquisitionTask


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
    test_acquisition_task,
):
    """Test filtering acquisition tasks."""

    response_roi = await async_client.get(
        f"/api/v2/acquisition-tasks?roi_id={test_roi.roi_id}"
    )
   

    assert response_roi.status_code == 200
    res_roi_data = response_roi.json()
    assert isinstance(res_roi_data, list)
  
    assert len(res_roi_data) >= 1, f"API call returned empty list, expected at least one task matching roi_id {test_roi.roi_id}"

    assert all(task["roi_ref"]["id"] == str(test_roi.id) for task in res_roi_data)
    assert any(
        task["task_id"] == test_acquisition_task.task_id for task in res_roi_data
    )

    response_block = await async_client.get(
        f"/api/v2/acquisition-tasks?block_id={test_block.block_id}"
    )
    assert response_block.status_code == 200
    res_block_data = response_block.json()
    assert isinstance(res_block_data, list)
    assert len(res_block_data) >= 1
    assert all(
        task["block_ref"]["id"] == str(test_block.id) for task in res_block_data
    )

    response_spec = await async_client.get(
        f"/api/v2/acquisition-tasks?specimen_id={test_specimen.specimen_id}"
    )
    assert response_spec.status_code == 200
    res_spec_data = response_spec.json()
    assert isinstance(res_spec_data, list)
    assert len(res_spec_data) >= 1
    assert all(
        task["specimen_ref"]["id"] == str(test_specimen.id) for task in res_spec_data
    )

    response_status = await async_client.get(
        f"/api/v2/acquisition-tasks?status={AcquisitionTaskStatus.PLANNED.value}"
    )
    assert response_status.status_code == 200
    res_status_data = response_status.json()
    assert isinstance(res_status_data, list)
    assert all(
        task["status"] == AcquisitionTaskStatus.PLANNED.value
        for task in res_status_data
    )


@pytest.mark.asyncio
async def test_create_acquisition_task(
    async_client: AsyncClient, test_specimen, test_block, test_roi
):
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
    assert (
        response_data["status"] == AcquisitionTaskStatus.PLANNED.value
    )  
    assert response_data["specimen_ref"]["id"] == str(test_specimen.id)
    assert response_data["block_ref"]["id"] == str(test_block.id)
    assert response_data["roi_ref"]["id"] == str(test_roi.id)

    # await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_hr}")


@pytest.mark.asyncio
async def test_create_acquisition_task_invalid_parent(
    async_client: AsyncClient, test_specimen, test_block
):
    """Test creating a task fails atomically if a parent doesn't exist (transaction test)."""
    task_id_hr = f"TASK_CREATE_INVALID_{int(datetime.now(timezone.utc).timestamp())}"
    invalid_roi_id = 9999999
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
    response = await async_client.get(
        f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["task_id"] == test_acquisition_task.task_id
    assert response_data["_id"] == str(test_acquisition_task.id)
    assert response_data["specimen_ref"]["id"] == str(
        test_acquisition_task.specimen_ref.ref.id
    )
    assert response_data["block_ref"]["id"] == str(test_acquisition_task.block_ref.ref.id)
    assert response_data["roi_ref"]["id"] == str(test_acquisition_task.roi_ref.ref.id)


@pytest.mark.asyncio
async def test_get_acquisition_task_not_found(async_client: AsyncClient):
    """Test retrieving a non-existent task."""
    response = await async_client.get("/api/v2/acquisition-tasks/NON_EXISTENT_TASK")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_acquisition_task(
    async_client: AsyncClient, test_acquisition_task
):
    """Test updating a task's status and metadata."""
    update_data = {
        "status": AcquisitionTaskStatus.IN_PROGRESS.value, 
        "metadata": {"updated_key": "updated_value"},
    }
    response = await async_client.patch(
        f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}", json=update_data
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == AcquisitionTaskStatus.IN_PROGRESS.value
    assert response_data["metadata"]["updated_key"] == "updated_value"
    assert response_data["task_id"] == test_acquisition_task.task_id
    assert "updated_at" in response_data
    assert response_data["updated_at"] is not None


@pytest.mark.asyncio
async def test_delete_task(
    async_client: AsyncClient, test_specimen, test_block, test_roi
):
    """Test deleting a task successfully (when it has no dependencies)."""
    task_id_hr = f"TASK_DELETE_{int(datetime.now(timezone.utc).timestamp())}"
    task_data = {
        "task_id": task_id_hr,
        "specimen_id": test_specimen.specimen_id,
        "block_id": test_block.block_id,
        "roi_id": test_roi.roi_id,
    }
    create_response = await async_client.post(
        "/api/v2/acquisition-tasks", json=task_data
    )
    assert create_response.status_code == 201

    # Delete the task
    delete_response = await async_client.delete(
        f"/api/v2/acquisition-tasks/{task_id_hr}"
    )
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
async def test_update_task_status(async_client: AsyncClient, test_acquisition_task):
    """Test updating task status via the dedicated endpoint."""
    status_update = {"status": AcquisitionTaskStatus.COMPLETED.value}
    response = await async_client.post(
        f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}/status",
        json=status_update,
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == AcquisitionTaskStatus.COMPLETED.value
    assert response_data["task_id"] == test_acquisition_task.task_id
    assert response_data["updated_at"] is not None


@pytest.mark.asyncio
async def test_create_tasks_batch(
    async_client: AsyncClient, test_specimen, test_block, test_roi
):
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
    response = await async_client.post(
        "/api/v2/acquisition-tasks/batch", json=tasks_data
    )
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2
    assert response_data[0]["task_id"] == task_id_1
    assert response_data[1]["task_id"] == task_id_2
    assert response_data[0]["status"] == AcquisitionTaskStatus.PLANNED.value
    assert response_data[1]["task_type"] == "alignment_task"
    assert response_data[0]["roi_ref"]["id"] == str(test_roi.id)
    assert response_data[1]["roi_ref"]["id"] == str(test_roi.id)

    # await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_1}")
    # await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_2}")

@pytest.mark.asyncio
async def test_create_tasks_batch_partial_success(
    async_client: AsyncClient, test_specimen, test_block, test_roi
):
    """Test that batch creation fails at the invalid task but keeps valid ones."""
    task_id_1 = f"TASK_BATCH_PART_1_{int(datetime.now(timezone.utc).timestamp())}"
    task_id_2 = f"TASK_BATCH_PART_2_{int(datetime.now(timezone.utc).timestamp())}"
    invalid_roi_id = 9999998
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
    response = await async_client.post(
        "/api/v2/acquisition-tasks/batch", json=tasks_data
    )
    assert response.status_code == 404
    assert f"ROI '{invalid_roi_id}' not found" in response.json()["detail"]

    get_resp_1 = await async_client.get(f"/api/v2/acquisition-tasks/{task_id_1}")
    assert get_resp_1.status_code == 200
    assert get_resp_1.json()["task_id"] == task_id_1
    
    get_resp_2 = await async_client.get(f"/api/v2/acquisition-tasks/{task_id_2}")
    assert get_resp_2.status_code == 404
    
    delete_resp = await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_1}")
    assert delete_resp.status_code == 204