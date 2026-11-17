import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()


def assert_missing_parent(response, parent: str, id: str | None):
    assert response.status_code == 404, response.text
    body = response.json()
    assert body["error_code"] == "MISSING_PARENT"
    assert body["context"] == {"parent": parent, "id": id}


@pytest.mark.parametrize("missing", ["substrate", "cutting session"])
async def test_section_create_names_its_missing_parent(
    async_client: AsyncClient, test_cutting_session, test_substrate, missing
):
    payload = {
        "cutting_session_id": "NO_SUCH_SESSION"
        if missing == "cutting session"
        else test_cutting_session.cutting_session_id,
        "media_id": "NO_SUCH_SUBSTRATE" if missing == "substrate" else test_substrate.media_id,
        "timestamp": NOW,
    }

    response = await async_client.post("/api/v2/sections", json=payload)

    assert_missing_parent(response, missing, "NO_SUCH_SUBSTRATE" if missing == "substrate" else "NO_SUCH_SESSION")


async def test_block_create_without_its_specimen(async_client: AsyncClient, init_db):
    response = await async_client.post("/api/v2/blocks", json={"block_id": "B1", "specimen_id": "NO_SUCH_SPECIMEN"})

    assert_missing_parent(response, "specimen", "NO_SUCH_SPECIMEN")


async def test_cutting_session_create_without_its_block(async_client: AsyncClient, test_specimen):
    response = await async_client.post(
        "/api/v2/cutting-sessions",
        json={
            "cutting_session_id": "CS_NO_BLOCK",
            "block_id": "NO_SUCH_BLOCK",
            "start_time": NOW,
            "sectioning_device": "Test Device",
            "media_type": "tape",
        },
    )

    assert_missing_parent(response, "block", "NO_SUCH_BLOCK")


async def test_task_create_without_its_roi(async_client: AsyncClient, test_specimen, test_block):
    response = await async_client.post(
        "/api/v2/acquisition-tasks",
        json={
            "task_id": "TASK_NO_ROI",
            "specimen_id": test_specimen.specimen_id,
            "block_id": test_block.block_id,
            "roi_id": "NO_SUCH_ROI",
        },
    )

    assert_missing_parent(response, "ROI", "NO_SUCH_ROI")


async def test_roi_create_without_its_section(async_client: AsyncClient, init_db):
    response = await async_client.post(
        "/api/v2/rois",
        json={"section_id": "NO_SUCH_SECTION", "created_at": NOW, "payload": {"vertices": [[0, 0], [1, 0], [1, 1]]}},
    )

    assert_missing_parent(response, "section", "NO_SUCH_SECTION")


def _acquisition(test_roi, test_acquisition_task, **fields) -> dict:
    return {
        "acquisition_id": "ACQ_MISSING_PARENT",
        "montage_id": "MON_MISSING_PARENT",
        "roi_id": test_roi.roi_id,
        "acquisition_task_id": test_acquisition_task.task_id,
        "hardware_settings": {"camera_model": "c", "camera_serial": "1", "camera_bit_depth": 8, "media_type": "tape"},
        "acquisition_settings": {
            "magnification": 1000,
            "spot_size": 1,
            "exposure_time": 1,
            "tile_size": [10, 10],
            "tile_overlap": 0.1,
            "saved_bit_depth": 8,
        },
        **fields,
    }


async def test_acquisition_create_without_its_microscope(async_client: AsyncClient, test_roi, test_acquisition_task):
    response = await async_client.post(
        "/api/v2/acquisitions", json=_acquisition(test_roi, test_acquisition_task, microscope_id="NO_SUCH_SCOPE")
    )

    assert_missing_parent(response, "microscope", "NO_SUCH_SCOPE")


async def test_a_parent_only_the_database_checks_is_named_too(
    async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope
):
    dataset_id = str(uuid.uuid4())

    response = await async_client.post(
        "/api/v2/acquisitions",
        json=_acquisition(
            test_roi, test_acquisition_task, microscope_id=test_microscope.microscope_id, dataset_id=dataset_id
        ),
    )

    assert_missing_parent(response, "dataset", dataset_id)
