from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

drawn = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)


def _roi(section_id: str, minutes: int = 0, **fields) -> dict:
    return {
        "section_id": section_id,
        "created_at": (drawn + timedelta(minutes=minutes)).isoformat(),
        "payload": {
            "vertices": [[0, 0], [10, 0], [10, 10]],
            "rotation_angle": 0.0,
            "buffer_size": 0.0,
        },
        **fields,
    }


async def _section(async_client: AsyncClient, cutting_session, aperture: int | None, minutes: int = 30) -> str:
    response = await async_client.post(
        "/api/v2/sections",
        json={
            "cutting_session_id": cutting_session.cutting_session_id,
            "media_id": "SUB001",
            "aperture_index": aperture,
            "timestamp": (drawn + timedelta(minutes=minutes)).isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["section_id"]


@pytest.mark.asyncio
async def test_roi_numbered_on_section_aperture(async_client: AsyncClient, test_section):
    first = await async_client.post("/api/v2/rois", json=_roi(test_section.section_id))
    second = await async_client.post("/api/v2/rois", json=_roi(test_section.section_id, minutes=1))

    assert (first.status_code, second.status_code) == (201, 201), (
        first.text,
        second.text,
    )
    assert [first.json()["roi_id"], second.json()["roi_id"]] == [
        "SUB001.A0000.R001",
        "SUB001.A0000.R002",
    ]
    assert (first.json()["substrate_media_id"], first.json()["aperture_index"]) == (
        "SUB001",
        0,
    )


@pytest.mark.asyncio
async def test_sections_share_aperture_numbers(async_client: AsyncClient, test_section, test_cutting_session):
    other = await _section(async_client, test_cutting_session, aperture=0)
    await async_client.post("/api/v2/rois", json=_roi(test_section.section_id))

    response = await async_client.post("/api/v2/rois", json=_roi(other, minutes=1))

    assert response.status_code == 201, response.text
    assert response.json()["roi_id"] == "SUB001.A0000.R002"


@pytest.mark.asyncio
async def test_no_aperture_on_substrate(async_client: AsyncClient, test_section, test_cutting_session):
    first_section = await _section(async_client, test_cutting_session, aperture=None)
    second_section = await _section(async_client, test_cutting_session, aperture=None, minutes=40)

    first = await async_client.post("/api/v2/rois", json=_roi(first_section))
    second = await async_client.post("/api/v2/rois", json=_roi(second_section, minutes=1))
    resent = await async_client.post("/api/v2/rois", json=_roi(first_section))

    assert [r.status_code for r in (first, second, resent)] == [201, 201, 200], (
        first.text,
        second.text,
    )
    assert [r.json()["roi_id"] for r in (first, second, resent)] == [
        "SUB001.R0001",
        "SUB001.R0002",
        "SUB001.R0001",
    ]
    assert first.json()["aperture_index"] is None


@pytest.mark.asyncio
async def test_no_section_is_422(async_client: AsyncClient, test_section):
    body = _roi(test_section.section_id)
    del body["section_id"]

    response = await async_client.post("/api/v2/rois", json=body)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_missing_section_is_404(async_client: AsyncClient, test_section):
    response = await async_client.post("/api/v2/rois", json=_roi("NO_SUCH_SECTION"))

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_substrate_or_aperture_field_is_422(async_client: AsyncClient, test_section):
    response = await async_client.post(
        "/api/v2/rois",
        json=_roi(test_section.section_id, substrate_media_id="SUB001", aperture_index=0),
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_sub_roi_parent_by_created_at(async_client: AsyncClient, test_section):
    parent = (await async_client.post("/api/v2/rois", json=_roi(test_section.section_id))).json()

    child = await async_client.post(
        "/api/v2/rois",
        json=_roi(test_section.section_id, minutes=5, parent_created_at=drawn.isoformat()),
    )

    assert child.status_code == 201, child.text
    assert (child.json()["roi_id"], child.json()["parent_roi_id"]) == (
        "SUB001.A0000.R002",
        parent["roi_id"],
    )


@pytest.mark.asyncio
async def test_fourth_level_is_422(async_client: AsyncClient, test_section):
    for level in range(3):
        parent = {"parent_created_at": (drawn + timedelta(minutes=level - 1)).isoformat()} if level else {}
        response = await async_client.post("/api/v2/rois", json=_roi(test_section.section_id, minutes=level, **parent))
        assert response.status_code == 201, response.text

    fourth = await async_client.post(
        "/api/v2/rois",
        json=_roi(
            test_section.section_id,
            minutes=3,
            parent_created_at=(drawn + timedelta(minutes=2)).isoformat(),
        ),
    )

    assert fourth.status_code == 422, fourth.text


@pytest.mark.asyncio
async def test_parent_on_other_section_is_404(async_client: AsyncClient, test_section, test_cutting_session):
    other = await _section(async_client, test_cutting_session, aperture=0)
    await async_client.post("/api/v2/rois", json=_roi(test_section.section_id))

    child = await async_client.post("/api/v2/rois", json=_roi(other, minutes=5, parent_created_at=drawn.isoformat()))

    assert child.status_code == 404, child.text


@pytest.mark.asyncio
async def test_resend_returns_stored_roi(async_client: AsyncClient, test_section):
    created = await async_client.post("/api/v2/rois", json=_roi(test_section.section_id))
    resent = await async_client.post("/api/v2/rois", json=_roi(test_section.section_id))
    listed = await async_client.get("/api/v2/rois")

    assert (created.status_code, resent.status_code) == (201, 200), resent.text
    assert resent.json()["roi_id"] == created.json()["roi_id"]
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_resend_new_rotation_angle_is_409(async_client: AsyncClient, test_section):
    await async_client.post("/api/v2/rois", json=_roi(test_section.section_id))
    moved = _roi(test_section.section_id)
    moved["payload"]["rotation_angle"] = 15.0

    response = await async_client.post("/api/v2/rois", json=moved)

    assert response.status_code == 409, response.text
    assert response.json()["error_code"] == "KEY_IN_USE"
    assert "rotation_angle" in response.json()["detail"]


@pytest.mark.asyncio
async def test_resend_other_section_is_409(async_client: AsyncClient, test_section, test_cutting_session):
    other = await _section(async_client, test_cutting_session, aperture=0)
    await async_client.post("/api/v2/rois", json=_roi(test_section.section_id))

    resent = await async_client.post("/api/v2/rois", json=_roi(other))

    assert resent.status_code == 409, resent.text
    assert "section_id" in resent.json()["detail"]


@pytest.mark.asyncio
async def test_resend_new_parent_is_409(async_client: AsyncClient, test_section):
    section_id = test_section.section_id
    await async_client.post("/api/v2/rois", json=_roi(section_id))
    await async_client.post("/api/v2/rois", json=_roi(section_id, minutes=1))
    await async_client.post(
        "/api/v2/rois",
        json=_roi(section_id, minutes=5, parent_created_at=drawn.isoformat()),
    )

    other_parent = await async_client.post(
        "/api/v2/rois",
        json=_roi(
            section_id,
            minutes=5,
            parent_created_at=(drawn + timedelta(minutes=1)).isoformat(),
        ),
    )
    no_parent = await async_client.post("/api/v2/rois", json=_roi(section_id, minutes=5))

    assert (other_parent.status_code, no_parent.status_code) == (409, 409), (
        other_parent.text,
        no_parent.text,
    )
    assert "parent_created_at" in other_parent.json()["detail"]


@pytest.mark.asyncio
async def test_list_by_aperture(async_client: AsyncClient, test_section, test_cutting_session):
    other = await _section(async_client, test_cutting_session, aperture=2)
    await async_client.post("/api/v2/rois", json=_roi(test_section.section_id))
    await async_client.post("/api/v2/rois", json=_roi(other))

    response = await async_client.get("/api/v2/rois", params={"substrate_media_id": "SUB001", "aperture_index": 2})

    assert response.status_code == 200, response.text
    assert [roi["roi_id"] for roi in response.json()] == ["SUB001.A0002.R001"]


@pytest.mark.asyncio
async def test_list_by_lineage(async_client: AsyncClient, test_section):
    roi = (await async_client.post("/api/v2/rois", json=_roi(test_section.section_id))).json()
    filters = [
        {"specimen_id": test_section.specimen_id},
        {"block_id": test_section.block_id},
        {"cutting_session_id": test_section.cutting_session_id},
    ]
    elsewhere = {"block_id": "OTHER_BLOCK"}

    listed = [(await async_client.get("/api/v2/rois", params=params)).json() for params in [*filters, elsewhere]]

    assert [[item["roi_id"] for item in rois] for rois in listed] == [[roi["roi_id"]]] * 3 + [[]]
