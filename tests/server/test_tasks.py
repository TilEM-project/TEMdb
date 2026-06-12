from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from temdb.server.api.v2.tasks import derive_task_state
from temdb.server.sqlmodels import AcquisitionSQLModel

_HARDWARE_SETTINGS = {
    "scope_id": "TEST_SCOPE_001",
    "camera_model": "Test Camera",
    "camera_serial": "12345",
    "camera_bit_depth": 16,
    "media_type": "tape",
}
_ACQUISITION_SETTINGS = {
    "magnification": 1000,
    "spot_size": 2,
    "exposure_time": 100,
    "tile_size": [4096, 4096],
    "tile_overlap": 0.1,
    "saved_bit_depth": 8,
}


def _run(status="complete", qc_state="pending", start_time=None):
    return AcquisitionSQLModel(
        status=status,
        qc_state=qc_state,
        start_time=start_time or datetime.now(timezone.utc),
    )


def test_derive_pending():
    assert derive_task_state([]) == "pending"


def test_derive_complete():
    assert derive_task_state([_run(qc_state="qc_pass")]) == "complete"


def test_derive_complete_wins_over_newer_failure():
    old = _run(qc_state="qc_pass", start_time=datetime.now(timezone.utc) - timedelta(hours=1))
    new = _run(status="failed")
    assert derive_task_state([old, new]) == "complete"


def test_derive_failed():
    assert derive_task_state([_run(status="failed"), _run(status="aborted")]) == "failed"


def test_derive_needs_review():
    assert derive_task_state([_run(qc_state="qc_fail")]) == "needs_review"


def test_derive_needs_review_only_for_newest_run():
    old = _run(qc_state="qc_fail", start_time=datetime.now(timezone.utc) - timedelta(hours=1))
    new = _run(status=None)
    assert derive_task_state([old, new]) == "acquired"


def test_derive_acquired():
    assert derive_task_state([_run()]) == "acquired"


def test_derive_acquired_in_flight():
    assert derive_task_state([_run(status=None)]) == "acquired"


@pytest.mark.asyncio
async def test_supersede_lifecycle(
    async_client: AsyncClient,
    test_acquisition_task,
    test_specimen,
    test_block,
    test_roi,
):
    old_id = test_acquisition_task.task_id
    before = (await async_client.get(f"/api/v2/acquisition-tasks/{old_id}")).json()
    assert before.get("superseded_by") is None

    new_payload = {
        "task_id": f"{old_id}_V2",
        "specimen_id": test_specimen.specimen_id,
        "block_id": test_block.block_id,
        "roi_id": test_roi.roi_id,
    }
    response = await async_client.post(f"/api/v2/acquisition-tasks/{old_id}/supersede", json=new_payload)
    assert response.status_code == 201
    new_task = response.json()
    assert new_task["task_id"] == f"{old_id}_V2"
    assert new_task["status"] == "pending"
    assert new_task["superseded_by"] is None

    after = (await async_client.get(f"/api/v2/acquisition-tasks/{old_id}")).json()
    assert after["superseded_by"] == new_task["task_id"]

    current = (await async_client.get("/api/v2/acquisition-tasks", params={"current_only": True})).json()
    current_ids = [t["task_id"] for t in current]
    assert old_id not in current_ids
    assert new_task["task_id"] in current_ids

    everything = (await async_client.get("/api/v2/acquisition-tasks", params={"current_only": False})).json()
    assert old_id in [t["task_id"] for t in everything]

    again = await async_client.post(
        f"/api/v2/acquisition-tasks/{old_id}/supersede",
        json={**new_payload, "task_id": f"{old_id}_V3"},
    )
    assert again.status_code == 409
    assert (await async_client.get(f"/api/v2/acquisition-tasks/{old_id}")).json()["superseded_by"] == new_task["task_id"]


@pytest.mark.asyncio
async def test_create_lens_correction_task_without_lineage(async_client: AsyncClient, init_db):
    response = await async_client.post(
        "/api/v2/acquisition-tasks",
        json={"task_id": "TEST_TASK_LC_001", "kind": "lens_correction"},
    )
    assert response.status_code == 201
    created = response.json()
    assert created["kind"] == "lens_correction"
    assert created["roi_id"] is None
    assert created["status"] == "pending"


@pytest.mark.asyncio
async def test_create_montage_task_without_lineage_rejected(async_client: AsyncClient, init_db):
    response = await async_client.post(
        "/api/v2/acquisition-tasks",
        json={"task_id": "TEST_TASK_NO_LINEAGE", "kind": "montage"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_task_invalid_kind_rejected(async_client: AsyncClient, init_db):
    response = await async_client.post(
        "/api/v2/acquisition-tasks",
        json={"task_id": "TEST_TASK_BAD_KIND", "kind": "calibration"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_imageable_work_fetch(
    async_client: AsyncClient,
    test_acquisition_task,
    test_microscope,
):
    task_id = test_acquisition_task.task_id

    pool = (await async_client.get("/api/v2/acquisition-tasks", params={"imageable": True})).json()
    assert task_id in [t["task_id"] for t in pool]

    acq_payload = {
        "acquisition_id": "TEST_ACQ_IMAGEABLE_001",
        "montage_id": "TEST_MONTAGE_IMAGEABLE_001",
        "roi_id": test_acquisition_task.roi_id,
        "acquisition_task_id": task_id,
        "microscope_id": str(test_microscope.microscope_id),
        "hardware_settings": _HARDWARE_SETTINGS,
        "acquisition_settings": _ACQUISITION_SETTINGS,
    }
    create_response = await async_client.post("/api/v2/acquisitions", json=acq_payload)
    assert create_response.status_code == 201
    acquisition_id = create_response.json()["acquisition_id"]

    pool = (await async_client.get("/api/v2/acquisition-tasks", params={"imageable": True})).json()
    assert task_id not in [t["task_id"] for t in pool]

    patch_response = await async_client.patch(f"/api/v2/acquisitions/{acquisition_id}", json={"status": "failed"})
    assert patch_response.status_code == 200

    pool = (await async_client.get("/api/v2/acquisition-tasks", params={"imageable": True})).json()
    assert task_id in [t["task_id"] for t in pool]


@pytest.mark.asyncio
async def test_imageable_blocked_by_complete_run_pending_qc(
    async_client: AsyncClient,
    test_acquisition_task,
    test_microscope,
):
    task_id = test_acquisition_task.task_id
    acq_payload = {
        "acquisition_id": "TEST_ACQ_QC_BLOCK_001",
        "montage_id": "TEST_MONTAGE_QC_BLOCK_001",
        "roi_id": test_acquisition_task.roi_id,
        "acquisition_task_id": task_id,
        "microscope_id": str(test_microscope.microscope_id),
        "hardware_settings": _HARDWARE_SETTINGS,
        "acquisition_settings": _ACQUISITION_SETTINGS,
    }
    create_response = await async_client.post("/api/v2/acquisitions", json=acq_payload)
    assert create_response.status_code == 201
    acquisition_id = create_response.json()["acquisition_id"]

    patch_response = await async_client.patch(f"/api/v2/acquisitions/{acquisition_id}", json={"status": "complete"})
    assert patch_response.status_code == 200

    pool = (await async_client.get("/api/v2/acquisition-tasks", params={"imageable": True})).json()
    assert task_id not in [t["task_id"] for t in pool]

    qc_response = await async_client.patch(f"/api/v2/acquisitions/{acquisition_id}", json={"qc_state": "qc_fail"})
    assert qc_response.status_code == 200

    pool = (await async_client.get("/api/v2/acquisition-tasks", params={"imageable": True})).json()
    assert task_id in [t["task_id"] for t in pool]


@pytest.mark.asyncio
async def test_imageable_filters_by_loaded_substrates(
    async_client: AsyncClient,
    test_acquisition_task,
    test_roi,
):
    task_id = test_acquisition_task.task_id
    media_id = test_roi.substrate_media_id

    lc_response = await async_client.post(
        "/api/v2/acquisition-tasks",
        json={"task_id": "TEST_TASK_LC_LOADED", "kind": "lens_correction"},
    )
    assert lc_response.status_code == 201

    pool = (
        await async_client.get(
            "/api/v2/acquisition-tasks",
            params={"imageable": True, "loaded_media_id": ["SOME_OTHER_SUBSTRATE"]},
        )
    ).json()
    pool_ids = [t["task_id"] for t in pool]
    assert task_id not in pool_ids
    assert "TEST_TASK_LC_LOADED" in pool_ids

    pool = (
        await async_client.get(
            "/api/v2/acquisition-tasks",
            params={"imageable": True, "loaded_media_id": [media_id]},
        )
    ).json()
    assert task_id in [t["task_id"] for t in pool]


@pytest.mark.asyncio
async def test_tilt_series_batch_groups(
    async_client: AsyncClient,
    test_specimen,
    test_block,
    test_roi,
):
    base = {
        "specimen_id": test_specimen.specimen_id,
        "block_id": test_block.block_id,
        "roi_id": test_roi.roi_id,
    }
    tasks = [
        {**base, "task_id": f"TEST_TASK_TILT_{index}", "tilt_angle_deg": angle}
        for index, angle in enumerate((0.0, 15.0, -15.0))
    ]
    response = await async_client.post("/api/v2/acquisition-tasks/batch", json={"tasks": tasks, "group": True})
    assert response.status_code == 201
    created = response.json()
    assert len(created) == 3
    group_ids = {t["task_group_id"] for t in created}
    assert len(group_ids) == 1
    assert None not in group_ids

    series = (
        await async_client.get("/api/v2/acquisition-tasks", params={"task_group_id": group_ids.pop()})
    ).json()
    assert [t["tilt_angle_deg"] for t in series] == [-15.0, 0.0, 15.0]


@pytest.mark.asyncio
async def test_batch_without_group_has_no_group_id(
    async_client: AsyncClient,
    test_specimen,
    test_block,
    test_roi,
):
    tasks = [
        {
            "task_id": "TEST_TASK_UNGROUPED_1",
            "specimen_id": test_specimen.specimen_id,
            "block_id": test_block.block_id,
            "roi_id": test_roi.roi_id,
        }
    ]
    response = await async_client.post("/api/v2/acquisition-tasks/batch", json={"tasks": tasks})
    assert response.status_code == 201
    assert response.json()[0]["task_group_id"] is None
