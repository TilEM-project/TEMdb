from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from temdb.server.sqlmodels import AcquisitionSQLModel, AcquisitionTaskSQLModel, ROISQLModel, SectionSQLModel


@pytest.mark.asyncio
async def test_list_acquisition_tasks_unfiltered(async_client: AsyncClient, test_acquisition_task):
    """Test retrieving a list of all acquisition tasks."""
    response = await async_client.get("/api/v2/acquisition-tasks")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert any(task["task_id"] == test_acquisition_task.task_id for task in response_data)


@pytest.mark.asyncio
async def test_list_acquisition_tasks_filtered(
    async_client: AsyncClient,
    test_specimen,
    test_block,
    test_roi,
    test_acquisition_task,
):
    """Test filtering acquisition tasks."""

    response_roi = await async_client.get(f"/api/v2/acquisition-tasks?roi_id={test_roi.roi_id}")

    assert response_roi.status_code == 200
    res_roi_data = response_roi.json()
    assert isinstance(res_roi_data, list)

    assert len(res_roi_data) >= 1, (
        f"API call returned empty list, expected at least one task matching roi_id {test_roi.roi_id}"
    )

    assert all(task["roi_id"] == test_roi.roi_id for task in res_roi_data)
    assert any(task["task_id"] == test_acquisition_task.task_id for task in res_roi_data)

    response_block = await async_client.get(f"/api/v2/acquisition-tasks?block_id={test_block.block_id}")
    assert response_block.status_code == 200
    res_block_data = response_block.json()
    assert isinstance(res_block_data, list)
    assert len(res_block_data) >= 1
    assert all(task["block_id"] == test_block.block_id for task in res_block_data)

    response_spec = await async_client.get(f"/api/v2/acquisition-tasks?specimen_id={test_specimen.specimen_id}")
    assert response_spec.status_code == 200
    res_spec_data = response_spec.json()
    assert isinstance(res_spec_data, list)
    assert len(res_spec_data) >= 1
    assert all(task["specimen_id"] == test_specimen.specimen_id for task in res_spec_data)

    response_kind = await async_client.get("/api/v2/acquisition-tasks?kind=montage")
    assert response_kind.status_code == 200
    res_kind_data = response_kind.json()
    assert isinstance(res_kind_data, list)
    assert all(task["kind"] == "montage" for task in res_kind_data)
    assert all(task["status"] == "pending" for task in res_kind_data)


@pytest.mark.asyncio
async def test_list_acquisition_tasks_skip_destroyed(
    async_client: AsyncClient,
    test_specimen,
    test_block,
    test_cutting_session,
    test_substrate,
    test_db_manager,
    test_acquisition_task,
):
    async with test_db_manager.async_session_factory() as session:
        destroyed_section = SectionSQLModel(
            section_id="TEST_SECTION_DESTROYED_001",
            section_number=2,
            timestamp=datetime.now(timezone.utc),
            cutting_session_id=test_cutting_session.cutting_session_id,
            block_id=test_block.block_id,
            specimen_id=test_specimen.specimen_id,
            media_id=test_substrate.media_id,
            condition="destroyed",
            created_at=datetime.now(timezone.utc),
        )
        session.add(destroyed_section)
        await session.commit()
        await session.refresh(destroyed_section)

        destroyed_roi = ROISQLModel(
            roi_id="SPEC001.BLK001.CS001.SEC002.SUB001.ROI001",
            roi_number=1,
            section_id=destroyed_section.section_id,
            block_id=test_block.block_id,
            specimen_id=test_specimen.specimen_id,
            substrate_media_id="SUB001",
            hierarchy_level=1,
            parent_roi_id=None,
            updated_at=datetime.now(timezone.utc),
            section_number=destroyed_section.section_number,
            roi_payload={},
            created_at=datetime.now(timezone.utc),
        )
        session.add(destroyed_roi)
        await session.commit()
        await session.refresh(destroyed_roi)

        destroyed_task = AcquisitionTaskSQLModel(
            task_id="TEST_TASK_DESTROYED_001",
            specimen_id=test_specimen.specimen_id,
            block_id=test_block.block_id,
            roi_id=destroyed_roi.roi_id,
            kind="montage",
            tags=[],
            metadata_json={},
            created_at=datetime.now(timezone.utc),
        )
        session.add(destroyed_task)
        await session.commit()

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
    test_acquisition_task2,
    test_db_manager,
    test_microscope,
):
    async with test_db_manager.async_session_factory() as session:
        failed_acquisition = AcquisitionSQLModel(
            acquisition_id="TEST_ACQ_QC_FAILED_001",
            montage_id="TEST_MONTAGE_QC_FAILED_001",
            specimen_id=test_specimen.specimen_id,
            roi_id=test_roi.roi_id,
            acquisition_task_id=test_acquisition_task.task_id,
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
            microscope_id=test_microscope.microscope_id,
            status="failed",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        passed_acquisition = AcquisitionSQLModel(
            acquisition_id="TEST_ACQ_QC_PASSED_001",
            montage_id="TEST_MONTAGE_QC_PASSED_001",
            specimen_id=test_specimen.specimen_id,
            roi_id=test_roi.roi_id,
            acquisition_task_id=test_acquisition_task.task_id,
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
            microscope_id=test_microscope.microscope_id,
            status="complete",
            qc_state="qc_pass",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
        )
        session.add(failed_acquisition)
        session.add(passed_acquisition)
        await session.commit()

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
    assert all(task["roi_id"] == test_roi2.roi_id for task in res_media_data)


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
    }
    response = await async_client.post("/api/v2/acquisition-tasks", json=task_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["task_id"] == task_id_hr
    assert response_data["status"] == "pending"
    assert response_data["kind"] == "montage"
    assert response_data["specimen_id"] == test_specimen.specimen_id
    assert response_data["block_id"] == test_block.block_id
    assert response_data["roi_id"] == test_roi.roi_id

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
    assert response_data["id"] == test_acquisition_task.id
    assert response_data["specimen_id"] == test_acquisition_task.specimen_id
    assert response_data["block_id"] == test_acquisition_task.block_id
    assert response_data["roi_id"] == test_acquisition_task.roi_id


@pytest.mark.asyncio
async def test_get_acquisition_task_not_found(async_client: AsyncClient):
    """Test retrieving a non-existent task."""
    response = await async_client.get("/api/v2/acquisition-tasks/NON_EXISTENT_TASK")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_acquisition_task(async_client: AsyncClient, test_acquisition_task):
    """Test updating a task's metadata; status stays derived from runs."""
    update_data = {
        "metadata": {"updated_key": "updated_value"},
        "tilt_angle_deg": 12.5,
    }
    response = await async_client.patch(f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}", json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "pending"
    assert response_data["metadata"]["updated_key"] == "updated_value"
    assert response_data["tilt_angle_deg"] == 12.5
    assert response_data["task_id"] == test_acquisition_task.task_id
    assert "updated_at" in response_data
    assert response_data["updated_at"] is not None


@pytest.mark.asyncio
async def test_update_acquisition_task_invalid_kind_rejected(
    async_client: AsyncClient, test_acquisition_task
):
    response = await async_client.patch(
        f"/api/v2/acquisition-tasks/{test_acquisition_task.task_id}",
        json={"kind": "bogus"},
    )
    assert response.status_code == 422


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
        },
    ]
    response = await async_client.post("/api/v2/acquisition-tasks/batch", json={"tasks": tasks_data})
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) == 2
    assert response_data[0]["task_id"] == task_id_1
    assert response_data[1]["task_id"] == task_id_2
    assert response_data[0]["status"] == "pending"
    assert response_data[1]["kind"] == "montage"
    assert response_data[0]["roi_id"] == test_roi.roi_id
    assert response_data[1]["roi_id"] == test_roi.roi_id

    # await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_1}")
    # await async_client.delete(f"/api/v2/acquisition-tasks/{task_id_2}")


@pytest.mark.asyncio
async def test_create_tasks_batch_atomic(async_client: AsyncClient, test_specimen, test_block, test_roi):
    """Test that batch creation is a single transaction: one invalid task rolls back all."""
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
    response = await async_client.post("/api/v2/acquisition-tasks/batch", json={"tasks": tasks_data})
    assert response.status_code == 404
    assert f"ROI '{invalid_roi_id}' not found" in response.json()["detail"]

    get_resp_1 = await async_client.get(f"/api/v2/acquisition-tasks/{task_id_1}")
    assert get_resp_1.status_code == 404

    get_resp_2 = await async_client.get(f"/api/v2/acquisition-tasks/{task_id_2}")
    assert get_resp_2.status_code == 404
