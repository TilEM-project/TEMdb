from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

drawn = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)


async def _roi(async_client: AsyncClient, section_id: str, minutes: int = 0, **fields) -> dict:
    body = {
        "section_id": section_id,
        "created_at": (drawn + timedelta(minutes=minutes)).isoformat(),
        "payload": {"vertices": [[0, 0], [10, 0], [10, 10]], "rotation_angle": 0.0},
        **fields,
    }
    response = await async_client.post("/api/v2/rois", json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def _task(async_client: AsyncClient, roi: dict, section) -> None:
    response = await async_client.post(
        "/api/v2/acquisition-tasks",
        json={
            "task_id": f"{roi['roi_id']}.hm2000",
            "roi_id": roi["roi_id"],
            "specimen_id": section.specimen_id,
            "block_id": section.block_id,
        },
    )
    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_unlinked_vertices_change(async_client: AsyncClient, test_section):
    roi = await _roi(async_client, test_section.section_id)

    response = await async_client.patch(
        f"/api/v2/rois/{roi['roi_id']}",
        json={"payload": {"vertices": [[1, 1], [11, 1], [11, 11]], "rotation_angle": 15.0, "buffer_size": 2.0}},
    )

    assert response.status_code == 200, response.text
    assert response.json()["roi_payload"]["rotation_angle"] == 15.0
    assert response.json()["roi_payload"]["vertices"] == [[1, 1], [11, 1], [11, 11]]


@pytest.mark.asyncio
async def test_task_locks_rotation_angle(async_client: AsyncClient, test_section):
    roi = await _roi(async_client, test_section.section_id)
    await _task(async_client, roi, test_section)
    path = f"/api/v2/rois/{roi['roi_id']}"

    rotated = await async_client.patch(path, json={"payload": {"rotation_angle": 15.0}})
    note = await async_client.patch(path, json={"payload": {"rule": "manual"}})

    assert rotated.status_code == 409, rotated.text
    assert note.status_code == 200, note.text


@pytest.mark.asyncio
async def test_sub_roi_locks_buffer_size(async_client: AsyncClient, test_section):
    parent = await _roi(async_client, test_section.section_id)
    await _roi(async_client, test_section.section_id, minutes=1, parent_created_at=drawn.isoformat())

    response = await async_client.patch(f"/api/v2/rois/{parent['roi_id']}", json={"payload": {"buffer_size": 5.0}})

    assert response.status_code == 409, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"section_id": "OTHER_SECTION"},
        {"substrate_media_id": "SUB001"},
        {"aperture_index": 2},
        {"created_at": "2026-10-23T11:00:00+00:00"},
        {"parent_created_at": "2026-10-23T10:00:00+00:00"},
    ],
)
async def test_identity_field_is_422(async_client: AsyncClient, test_section, change):
    roi = await _roi(async_client, test_section.section_id, minutes=1)

    response = await async_client.patch(f"/api/v2/rois/{roi['roi_id']}", json=change)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_roi_locks_section_aperture(async_client: AsyncClient, test_section):
    await _roi(async_client, test_section.section_id)

    response = await async_client.patch(f"/api/v2/sections/{test_section.section_id}", json={"aperture_index": 1})

    assert response.status_code == 409, response.text
