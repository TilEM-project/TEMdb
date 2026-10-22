from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

start = datetime(2026, 9, 4, 16, 0, tzinfo=timezone.utc)


def _section(cutting_session, media_id: str, minute: int, aperture: int | None = 0, **fields) -> dict:
    return {
        "cutting_session_id": cutting_session.cutting_session_id,
        "media_id": media_id,
        "aperture_index": aperture,
        "timestamp": (start + timedelta(minutes=minute)).isoformat(),
        **fields,
    }


def _path(cutting_session, section_id: str) -> str:
    return f"/api/v2/sections/sessions/{cutting_session.cutting_session_id}/sections/{section_id}"


@pytest.mark.asyncio
async def test_several_sections_on_one_aperture_at_different_times_are_kept_apart(
    async_client: AsyncClient, test_cutting_session, test_substrate
):
    first = await async_client.post("/api/v2/sections", json=_section(test_cutting_session, "SUB001", 0, 1))
    second = await async_client.post("/api/v2/sections", json=_section(test_cutting_session, "SUB001", 3, 1))

    assert (first.status_code, second.status_code) == (201, 201)
    assert first.json()["section_id"] != second.json()["section_id"]


@pytest.mark.asyncio
async def test_a_lost_cut_is_created_lost_without_an_aperture(
    async_client: AsyncClient, test_cutting_session, test_substrate
):
    lost = _section(test_cutting_session, "SUB001", 0, None, condition="lost", condition_reason="lost in pickup")

    created = await async_client.post("/api/v2/sections", json=lost)
    resent = await async_client.post("/api/v2/sections", json=lost)

    assert (created.status_code, resent.status_code) == (201, 200), created.text
    assert (created.json()["condition"], created.json()["aperture_index"]) == ("lost", None)


@pytest.mark.asyncio
async def test_a_qc_failure_is_created_damaged_with_its_reason(
    async_client: AsyncClient, test_cutting_session, test_substrate
):
    response = await async_client.post(
        "/api/v2/sections",
        json=_section(test_cutting_session, "SUB001", 0, 2, condition="damaged", condition_reason="QC: no section"),
    )

    assert response.status_code == 201, response.text
    assert (response.json()["condition"], response.json()["condition_reason"]) == ("damaged", "QC: no section")


@pytest.mark.asyncio
async def test_a_condition_outside_the_vocabulary_is_422(
    async_client: AsyncClient, test_cutting_session, test_substrate
):
    response = await async_client.post(
        "/api/v2/sections", json=_section(test_cutting_session, "SUB001", 0, condition="missing")
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_a_missed_placement_keeps_its_nearest_aperture_and_position_and_marks_it_used(
    async_client: AsyncClient, test_cutting_session, test_substrate
):
    response = await async_client.post(
        "/api/v2/sections",
        json=_section(test_cutting_session, "SUB001", 0, 1, position={"x": 6.5, "y": 2.0}),
    )

    assert response.status_code == 201, response.text
    assert (response.json()["aperture_index"], response.json()["position"]) == (1, {"x": 6.5, "y": 2.0})
    statuses = (await async_client.get("/api/v2/substrates/SUB001")).json()["aperture_status"]
    assert statuses[1] == "used"


@pytest.mark.asyncio
async def test_correcting_an_aperture_onto_another_sections_placement_is_409(
    async_client: AsyncClient, test_cutting_session, test_substrate
):
    await async_client.post("/api/v2/sections", json=_section(test_cutting_session, "SUB001", 0, 1))
    other = (await async_client.post("/api/v2/sections", json=_section(test_cutting_session, "SUB001", 0, 2))).json()

    moved_onto = await async_client.patch(_path(test_cutting_session, other["section_id"]), json={"aperture_index": 1})
    moved_free = await async_client.patch(_path(test_cutting_session, other["section_id"]), json={"aperture_index": 0})

    assert (moved_onto.status_code, moved_free.status_code) == (409, 200)


@pytest.mark.asyncio
async def test_a_section_moved_to_another_substrate_is_a_new_section_and_the_old_one_lost(
    async_client: AsyncClient, test_cutting_session, test_substrate, test_layout
):
    await async_client.post(
        "/api/v2/substrates", json={"media_id": "SUB002", "substrate_layout_id": test_layout.layout_id}
    )
    old = (await async_client.post("/api/v2/sections", json=_section(test_cutting_session, "SUB001", 0))).json()

    new = await async_client.post("/api/v2/sections", json=_section(test_cutting_session, "SUB002", 0))
    lost = await async_client.patch(
        _path(test_cutting_session, old["section_id"]),
        json={"condition": "lost", "condition_reason": "moved to SUB002"},
    )

    assert (new.status_code, lost.status_code) == (201, 200)
    assert (new.json()["section_id"], lost.json()["condition"]) == ("SUB002_S1", "lost")


@pytest.mark.asyncio
async def test_a_resend_after_the_condition_changed_returns_the_stored_section(
    async_client: AsyncClient, test_cutting_session, test_substrate
):
    body = _section(test_cutting_session, "SUB001", 0)
    created = (await async_client.post("/api/v2/sections", json=body)).json()
    await async_client.patch(_path(test_cutting_session, created["section_id"]), json={"condition": "destroyed"})

    resent = await async_client.post("/api/v2/sections", json=body)

    assert resent.status_code == 200, resent.text
    assert resent.json()["condition"] == "destroyed"
