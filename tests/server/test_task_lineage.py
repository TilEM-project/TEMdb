from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

drawn = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)


async def _roi(async_client: AsyncClient, section_id: str) -> str:
    response = await async_client.post(
        "/api/v2/rois",
        json={
            "section_id": section_id,
            "created_at": drawn.isoformat(),
            "payload": {"vertices": [[0, 0], [10, 0], [10, 10]], "rotation_angle": 0.0},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["roi_id"]


def _task(roi_id: str, **lineage) -> dict:
    return {"task_id": f"{roi_id}.hm2000", "roi_id": roi_id, **lineage}


@pytest.mark.asyncio
@pytest.mark.parametrize("missing", ["specimen_id", "block_id"])
async def test_partial_lineage_is_422(async_client: AsyncClient, test_section, missing):
    roi_id = await _roi(async_client, test_section.section_id)
    lineage = {"specimen_id": test_section.specimen_id, "block_id": test_section.block_id}
    del lineage[missing]

    response = await async_client.post("/api/v2/acquisition-tasks", json=_task(roi_id, **lineage))

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_lineage_mismatch_is_400(async_client: AsyncClient, test_section):
    roi_id = await _roi(async_client, test_section.section_id)
    other_block = await async_client.post(
        "/api/v2/blocks", json={"block_id": "OTHER_BLOCK", "specimen_id": test_section.specimen_id}
    )
    assert other_block.status_code == 201, other_block.text

    mismatching = await async_client.post(
        "/api/v2/acquisition-tasks",
        json=_task(roi_id, specimen_id=test_section.specimen_id, block_id="OTHER_BLOCK"),
    )
    matching = await async_client.post(
        "/api/v2/acquisition-tasks",
        json=_task(roi_id, specimen_id=test_section.specimen_id, block_id=test_section.block_id),
    )

    assert (mismatching.status_code, matching.status_code) == (400, 201), (mismatching.text, matching.text)
