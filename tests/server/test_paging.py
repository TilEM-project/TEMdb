from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

LIMIT = 3
COUNTS = [LIMIT - 1, LIMIT, LIMIT + 1, 2 * LIMIT]


async def _all_pages(async_client: AsyncClient, path: str, key: str, **params) -> tuple[list[str], set[int]]:
    seen, totals, cursor = [], set(), None
    while True:
        query = {"limit": LIMIT, **params, **({"cursor": cursor} if cursor else {})}
        response = await async_client.get(path, params=query)
        assert response.status_code == 200, response.text
        body = response.json()
        seen += [row[key] for row in body["items"]]
        totals.add(body["total"])
        cursor = body["next_cursor"]
        if cursor is None:
            return seen, totals


async def _create_specimens(async_client: AsyncClient, specimen_ids):
    for specimen_id in specimen_ids:
        created = await async_client.post("/api/v2/specimens", json={"specimen_id": specimen_id})
        assert created.status_code == 201, created.text


@pytest.mark.parametrize("count", COUNTS)
async def test_specimen_pages_cover_every_row_once(async_client: AsyncClient, init_db, count):
    """Following next_cursor returns every specimen once, and every page reports the same total."""
    expected = [f"PAGED_SPECIMEN_{i}" for i in range(count)]
    await _create_specimens(async_client, expected)

    seen, totals = await _all_pages(async_client, "/api/v2/specimens", "specimen_id")

    assert seen == expected
    assert totals == {count}


async def test_offset_jump_then_cursor_covers_rest(async_client: AsyncClient, init_db):
    """A page fetched by offset carries a next_cursor that continues from it."""
    expected = [f"PAGED_SPECIMEN_{i}" for i in range(7)]
    await _create_specimens(async_client, expected)

    first = (await async_client.get("/api/v2/specimens", params={"offset": 3, "limit": 2})).json()
    rest, _ = await _all_pages(async_client, "/api/v2/specimens", "specimen_id", cursor=first["next_cursor"])

    assert [row["specimen_id"] for row in first["items"]] + rest == expected[3:]


async def test_offset_past_end_is_empty(async_client: AsyncClient, init_db):
    """An offset at the total returns no items and no next_cursor."""
    await _create_specimens(async_client, ["PAGED_SPECIMEN_0", "PAGED_SPECIMEN_1"])

    body = (await async_client.get("/api/v2/specimens", params={"offset": 2, "limit": 2})).json()

    assert body == {"items": [], "next_cursor": None, "total": 2}


async def test_inserted_row_is_not_repeated(async_client: AsyncClient, init_db):
    """A row created before the cursor between two pages does not shift the next page."""
    await _create_specimens(async_client, ["S1", "S3", "S5"])

    first = (await async_client.get("/api/v2/specimens", params={"limit": 2})).json()
    await _create_specimens(async_client, ["S2"])
    second = (await async_client.get("/api/v2/specimens", params={"limit": 2, "cursor": first["next_cursor"]})).json()

    assert [row["specimen_id"] for row in first["items"] + second["items"]] == ["S1", "S3", "S5"]


async def test_null_sort_values_page_once(async_client: AsyncClient, test_specimen, test_block, test_roi):
    """Tasks whose tilt_angle_deg is null are paged once like the others."""
    base = {"specimen_id": test_specimen.specimen_id, "block_id": test_block.block_id, "roi_id": test_roi.roi_id}
    angles = (None, 15.0, None, -15.0, 0.0)
    tasks = [{**base, "task_id": f"PAGED_TILT_{i}", "tilt_angle_deg": angle} for i, angle in enumerate(angles)]
    created = await async_client.post("/api/v2/acquisition-tasks/batch", json={"tasks": tasks, "group": True})
    assert created.status_code == 201, created.text
    group_id = created.json()[0]["task_group_id"]

    seen, _ = await _all_pages(async_client, "/api/v2/acquisition-tasks", "task_id", task_group_id=group_id, limit=2)

    assert sorted(seen) == sorted(task["task_id"] for task in tasks)
    assert len(seen) == len(tasks)


@pytest.mark.parametrize("path", ["/api/v2/acquisition-tasks", "/api/v2/specimens"])
async def test_foreign_cursor_is_refused(async_client: AsyncClient, init_db, path):
    """A cursor from another listing, or one that does not decode, is refused."""
    await _create_specimens(async_client, ["S1", "S2"])
    token = (await async_client.get("/api/v2/specimens", params={"limit": 1})).json()["next_cursor"]

    for cursor in ([token] if path != "/api/v2/specimens" else []) + ["garbage"]:
        response = await async_client.get(path, params={"cursor": cursor})
        assert response.status_code == 422, response.text
        assert response.json()["detail"] == "cursor is not from this listing"


async def test_after_with_offset_is_refused(async_client: AsyncClient, init_db):
    """Sending both cursor and offset is refused."""
    await _create_specimens(async_client, ["S1", "S2"])
    token = (await async_client.get("/api/v2/specimens", params={"limit": 1})).json()["next_cursor"]

    response = await async_client.get("/api/v2/specimens", params={"cursor": token, "offset": 1})

    assert response.status_code == 422, response.text


@pytest.fixture
async def tied_sections(async_client: AsyncClient, test_cutting_session, test_substrate, test_layout):
    other = await async_client.post(
        "/api/v2/substrates",
        json={"media_id": "PAGED_SUB002", "substrate_layout_id": test_layout.layout_id},
    )
    assert other.status_code == 201, other.text

    async def seed(count: int) -> list[str]:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        section_ids = []
        for i in range(count):
            created = await async_client.post(
                "/api/v2/sections",
                json={
                    "cutting_session_id": test_cutting_session.cutting_session_id,
                    "media_id": (test_substrate.media_id, "PAGED_SUB002")[i % 2],
                    "aperture_index": 0,
                    "timestamp": (start + timedelta(minutes=i)).isoformat(),
                },
            )
            assert created.status_code in (200, 201), created.text
            section_ids.append(created.json()["section_id"])
        return section_ids

    return seed


@pytest.mark.parametrize("count", COUNTS)
@pytest.mark.parametrize("listing", ["session", "all"])
async def test_tied_section_pages_cover_every_row_once(
    async_client: AsyncClient, tied_sections, test_cutting_session, listing, count
):
    """Sections sharing a section number on two substrates are each paged once."""
    expected = await tied_sections(count)
    path = {
        "session": f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}",
        "all": "/api/v2/sections",
    }[listing]

    seen, totals = await _all_pages(async_client, path, "section_id")

    assert sorted(seen) == sorted(expected)
    assert len(seen) == len(expected)
    assert totals == {count}
