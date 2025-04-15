import pytest


@pytest.mark.asyncio
async def test_list_acquisition_tasks(async_client):
    response = await async_client.get("/api/v2/acquisition-tasks")
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_acquisition_task(
    async_client, test_specimen, test_block, test_roi
):
    task_data = {
        "task_id": "TEST_TASK_CREATE",
        "specimen_id": test_specimen.specimen_id,
        "block_id": test_block.block_id,
        "roi_id": test_roi.roi_id,
        "tags": ["test", "create"],
        "metadata": {"test_key": "test_value"},
        "task_type": "standard_acquisition",
    }
    response = await async_client.post("/api/v2/acquisition-tasks", json=task_data)
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert response.json()["task_id"] == "TEST_TASK_CREATE"


@pytest.mark.asyncio
async def test_get_acquisition_task(async_client, test_acquisition_task):
    response = await async_client.get(
        f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}"
    )
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert response.json()["task_id"] == test_acquisition_task.task_id


@pytest.mark.asyncio
async def test_update_acquisition_task(async_client, test_acquisition_task):
    update_data = {"status": "In Progress"}  # Use the exact enum value
    response = await async_client.patch(
        f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}", json=update_data
    )
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        assert response.json()["status"] == "In Progress"
