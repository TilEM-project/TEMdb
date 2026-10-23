import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

start = datetime(2026, 9, 4, 16, 0, tzinfo=timezone.utc)


def _section(test_cutting_session, test_substrate, minute: int, aperture: int | None = 0, **fields) -> dict:
    return {
        "cutting_session_id": test_cutting_session.cutting_session_id,
        "media_id": test_substrate.media_id,
        "aperture_index": aperture,
        "timestamp": (start + timedelta(minutes=minute)).isoformat(),
        **fields,
    }


@pytest.mark.asyncio
async def test_numbered_per_substrate(async_client: AsyncClient, test_cutting_session, test_substrate):
    first = await async_client.post("/api/v2/sections", json=_section(test_cutting_session, test_substrate, 0, 0))
    second = await async_client.post("/api/v2/sections", json=_section(test_cutting_session, test_substrate, 1, 1))

    assert first.status_code == 201, first.text
    assert (first.json()["section_number"], first.json()["section_id"]) == (1, "SUB001_S1")
    assert (second.json()["section_number"], second.json()["section_id"]) == (2, "SUB001_S2")


@pytest.mark.asyncio
async def test_client_section_number_is_rejected(async_client: AsyncClient, test_cutting_session, test_substrate):
    response = await async_client.post(
        "/api/v2/sections", json=_section(test_cutting_session, test_substrate, 0, section_number=7)
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_create_without_timestamp_is_422(async_client: AsyncClient, test_cutting_session, test_substrate):
    body = _section(test_cutting_session, test_substrate, 0)
    del body["timestamp"]

    response = await async_client.post("/api/v2/sections", json=body)

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_resend_returns_stored(async_client: AsyncClient, test_cutting_session, test_substrate):
    body = _section(test_cutting_session, test_substrate, 0, cut_count=5)
    created = await async_client.post("/api/v2/sections", json=body)

    resent = await async_client.post("/api/v2/sections", json=body)

    assert resent.status_code == 200, resent.text
    assert resent.json()["section_id"] == created.json()["section_id"]
    listed = await async_client.get("/api/v2/sections", params={"media_id": test_substrate.media_id})
    assert len(listed.json()) == 1


@pytest.mark.asyncio
async def test_same_placement_different_values_is_409(async_client: AsyncClient, test_cutting_session, test_substrate):
    await async_client.post("/api/v2/sections", json=_section(test_cutting_session, test_substrate, 0, cut_count=5))

    response = await async_client.post(
        "/api/v2/sections", json=_section(test_cutting_session, test_substrate, 0, cut_count=6)
    )

    assert response.status_code == 409, response.text
    assert response.json()["error_code"] == "KEY_IN_USE"


@pytest.mark.asyncio
async def test_cut_count_may_repeat(async_client: AsyncClient, test_cutting_session, test_substrate):
    first = await async_client.post(
        "/api/v2/sections", json=_section(test_cutting_session, test_substrate, 0, 0, cut_count=3)
    )
    second = await async_client.post(
        "/api/v2/sections", json=_section(test_cutting_session, test_substrate, 1, 1, cut_count=3)
    )

    assert second.status_code == 201, second.text
    assert [first.json()["cut_count"], second.json()["cut_count"]] == [3, 3]


@pytest.mark.asyncio
async def test_lost_cuts_are_numbered_and_resendable(async_client: AsyncClient, test_cutting_session, test_substrate):
    lost = _section(test_cutting_session, test_substrate, 0, aperture=None)
    created = await async_client.post("/api/v2/sections", json=lost)
    resent = await async_client.post("/api/v2/sections", json=lost)
    other = await async_client.post(
        "/api/v2/sections", json=_section(test_cutting_session, test_substrate, 1, aperture=None)
    )

    assert (created.status_code, resent.status_code, other.status_code) == (201, 200, 201)
    assert [created.json()["section_number"], other.json()["section_number"]] == [1, 2]


@pytest.mark.asyncio
async def test_concurrent_creates_get_distinct_numbers(async_client: AsyncClient, test_cutting_session, test_substrate):
    responses = await asyncio.gather(
        *(
            async_client.post("/api/v2/sections", json=_section(test_cutting_session, test_substrate, minute, 0))
            for minute in range(8)
        )
    )

    assert [response.status_code for response in responses] == [201] * 8
    assert sorted(response.json()["section_number"] for response in responses) == list(range(1, 9))


@pytest.mark.asyncio
async def test_section_number_cannot_be_patched(async_client: AsyncClient, test_cutting_session, test_substrate):
    created = (
        await async_client.post("/api/v2/sections", json=_section(test_cutting_session, test_substrate, 0))
    ).json()

    response = await async_client.patch(
        f"/api/v2/sections/{created['section_id']}",
        json={"section_number": 9},
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_batch_numbers_in_request_order(async_client: AsyncClient, test_cutting_session, test_substrate):
    batch = [_section(test_cutting_session, test_substrate, minute, minute) for minute in range(3)]
    created = await async_client.post("/api/v2/sections/batch", json=batch)
    resent = await async_client.post("/api/v2/sections/batch", json=batch)

    assert created.status_code == 201, created.text
    assert [s["section_number"] for s in created.json()] == [1, 2, 3]
    assert [s["section_id"] for s in resent.json()] == [s["section_id"] for s in created.json()]


@pytest.mark.asyncio
async def test_duplicate_placement_in_batch_is_422(async_client: AsyncClient, test_cutting_session, test_substrate):
    section = _section(test_cutting_session, test_substrate, 0)

    response = await async_client.post("/api/v2/sections/batch", json=[section, section])

    assert response.status_code == 422, response.text
