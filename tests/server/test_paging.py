from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from temdb.models import HAS_MORE_HEADER

LIMIT = 3
COUNTS = [LIMIT - 1, LIMIT, LIMIT + 1, 2 * LIMIT]


async def _all_pages(async_client: AsyncClient, path: str, key: str) -> tuple[list[str], list[str]]:
    seen, flags, skip = [], [], 0
    while True:
        response = await async_client.get(path, params={"skip": skip, "limit": LIMIT})
        assert response.status_code == 200, response.text
        seen += [row[key] for row in response.json()]
        flags.append(response.headers[HAS_MORE_HEADER])
        if flags[-1] == "false":
            return seen, flags
        skip += LIMIT


def _assert_every_row_once(seen, flags, expected):
    assert sorted(seen) == sorted(expected)
    assert len(seen) == len(expected)
    assert flags[-1] == "false" and set(flags[:-1]) <= {"true"}


@pytest.mark.parametrize("count", COUNTS)
async def test_specimen_pages_cover_every_row_once(async_client: AsyncClient, init_db, count):
    expected = [f"PAGED_SPECIMEN_{i}" for i in range(count)]
    for specimen_id in expected:
        created = await async_client.post("/api/v2/specimens", json={"specimen_id": specimen_id})
        assert created.status_code == 201, created.text

    seen, flags = await _all_pages(async_client, "/api/v2/specimens", "specimen_id")

    _assert_every_row_once(seen, flags, expected)


async def test_browsers_may_read_the_has_more_header(async_client: AsyncClient, init_db):
    response = await async_client.get("/api/v2/specimens", headers={"Origin": "http://localhost:5173"})

    assert response.status_code == 200, response.text
    exposed = [name.strip().lower() for name in response.headers["access-control-expose-headers"].split(",")]
    assert HAS_MORE_HEADER.lower() in exposed


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
    expected = await tied_sections(count)
    path = {
        "session": f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}",
        "all": "/api/v2/sections",
    }[listing]

    seen, flags = await _all_pages(async_client, path, "section_id")

    _assert_every_row_once(seen, flags, expected)
