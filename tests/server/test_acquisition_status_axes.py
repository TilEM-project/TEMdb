import uuid

import pytest
from httpx import AsyncClient

MINIMAL_ACQ_PAYLOAD = {
    "acquisition_id": "ACQ_AXES_001",
    "montage_id": "MONTAGE_AXES_001",
    "hardware_settings": {
        "scope_id": "TEST_SCOPE_001",
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
}


@pytest.mark.asyncio
async def test_status_axes_independent(async_client: AsyncClient, test_acquisition):
    assert test_acquisition.status is None
    assert test_acquisition.qc_state == "pending"
    assert test_acquisition.transfer_state == "not_started"
    r = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}",
        json={"qc_state": "qc_pass", "updated_by": "qc-service"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["qc_state"] == "qc_pass"
    assert body["status"] == test_acquisition.status
    assert body["transfer_state"] == "not_started"
    assert body["qc_state_updated_by"] == "qc-service"
    assert body["qc_state_updated_at"] is not None


@pytest.mark.asyncio
async def test_invalid_qc_state_rejected(async_client: AsyncClient, test_acquisition):
    r = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}",
        json={"qc_state": "passed"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_returns_run_id_in_flight(
    async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope
):
    r = await async_client.post(
        "/api/v2/acquisitions",
        json={
            **MINIMAL_ACQ_PAYLOAD,
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "microscope_id": str(test_microscope.microscope_id),
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert uuid.UUID(body["run_id"])
    assert body["kind"] == "montage"
    assert body["status"] is None  # in flight until terminal write
    assert body["end_time"] is None
    assert body["microscope_id"] == str(test_microscope.microscope_id)
    assert body["qc_state"] == "pending"
    assert body["transfer_state"] == "not_started"


@pytest.mark.asyncio
async def test_create_requires_microscope(
    async_client: AsyncClient, test_roi, test_acquisition_task
):
    r = await async_client.post(
        "/api/v2/acquisitions",
        json={
            **MINIMAL_ACQ_PAYLOAD,
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_unknown_microscope_404(
    async_client: AsyncClient, test_roi, test_acquisition_task
):
    r = await async_client.post(
        "/api/v2/acquisitions",
        json={
            **MINIMAL_ACQ_PAYLOAD,
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "microscope_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_montage_requires_lineage(
    async_client: AsyncClient, test_acquisition_task, test_microscope
):
    r = await async_client.post(
        "/api/v2/acquisitions",
        json={
            **MINIMAL_ACQ_PAYLOAD,
            "acquisition_task_id": test_acquisition_task.task_id,
            "microscope_id": str(test_microscope.microscope_id),
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_unknown_lc_404(
    async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope
):
    r = await async_client.post(
        "/api/v2/acquisitions",
        json={
            **MINIMAL_ACQ_PAYLOAD,
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "microscope_id": str(test_microscope.microscope_id),
            "lc_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_status_write_once_at_termination(
    async_client: AsyncClient, test_acquisition
):
    acq_id = test_acquisition.acquisition_id
    assert test_acquisition.status is None
    r = await async_client.patch(
        f"/api/v2/acquisitions/{acq_id}", json={"status": "complete"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "complete"
    assert body["end_time"] is not None  # set together with the terminal status
    r = await async_client.patch(
        f"/api/v2/acquisitions/{acq_id}", json={"status": "failed"}
    )
    assert r.status_code == 409  # terminal status is write-once


@pytest.mark.asyncio
async def test_running_is_not_a_status(async_client: AsyncClient, test_acquisition):
    assert test_acquisition.status is None
    r = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}",
        json={"status": "running"},
    )
    assert r.status_code == 422  # NULL means in flight;


@pytest.mark.asyncio
async def test_transfer_state_axis_stamped(async_client: AsyncClient, test_acquisition):
    assert test_acquisition.transfer_state == "not_started"
    r = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}",
        json={"transfer_state": "in_progress", "updated_by": "transfer-service"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["transfer_state"] == "in_progress"
    assert body["transfer_state_updated_by"] == "transfer-service"
    assert body["transfer_state_updated_at"] is not None
    assert body["status"] is None
    assert body["qc_state"] == "pending"


@pytest.mark.asyncio
async def test_rollups_settable_via_patch(async_client: AsyncClient, test_acquisition):
    r = await async_client.patch(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}",
        json={
            "tile_count": 100,
            "avg_focus_score": 0.91,
            "failed_tile_count": 2,
            "median_match_quality": 0.88,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["tile_count"] == 100
    assert body["avg_focus_score"] == pytest.approx(0.91)
    assert body["failed_tile_count"] == 2
    assert body["median_match_quality"] == pytest.approx(0.88)
    assert body["status"] is None


@pytest.mark.asyncio
async def test_list_in_flight_and_qc_state_filters(
    async_client: AsyncClient, test_acquisition
):
    r = await async_client.get("/api/v2/acquisitions?status=in_flight")
    assert r.status_code == 200
    acqs = r.json()["acquisitions"]
    assert any(a["acquisition_id"] == test_acquisition.acquisition_id for a in acqs)
    assert all(a["status"] is None for a in acqs)

    r = await async_client.get("/api/v2/acquisitions?qc_state=pending&kind=montage")
    assert r.status_code == 200
    acqs = r.json()["acquisitions"]
    assert any(a["acquisition_id"] == test_acquisition.acquisition_id for a in acqs)

    r = await async_client.get("/api/v2/acquisitions?qc_state=qc_fail")
    assert r.status_code == 200
    assert all(
        a["acquisition_id"] != test_acquisition.acquisition_id
        for a in r.json()["acquisitions"]
    )
