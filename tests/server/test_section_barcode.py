from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


def _section(cutting_session, **fields) -> dict:
    return {
        "cutting_session_id": cutting_session.cutting_session_id,
        "media_id": "SUB001",
        "aperture_index": 0,
        "timestamp": datetime(2026, 9, 4, 16, 0, tzinfo=timezone.utc).isoformat(),
        **fields,
    }


async def _gridtape(async_client: AsyncClient, *media_ids: str) -> None:
    """GridTape GT-EM-70-2.0-1.5-2500: 2,500 film-coated 2.0 x 1.5 mm slots on a 6.0 mm pitch, one tape per media_id.
    The leaders carry no film, so they are not apertures."""
    layout = {
        "layout_id": "GT-EM-70-2.0-1.5-2500",
        "media_type": "tape",
        "apertures": [
            {"shape_type": "slot", "shape_params": {"width": 2.0, "height": 1.5}, "centroid": [6.0 * slot, 0.0]}
            for slot in range(2500)
        ],
    }
    assert (await async_client.post("/api/v2/layouts", json=layout)).status_code == 201
    for media_id in media_ids:
        tape = {"media_id": media_id, "substrate_layout_id": "GT-EM-70-2.0-1.5-2500"}
        assert (await async_client.post("/api/v2/substrates", json=tape)).status_code == 201


@pytest.mark.asyncio
async def test_create_rejects_barcode(async_client: AsyncClient, test_cutting_session, test_substrate):
    response = await async_client.post("/api/v2/sections", json=_section(test_cutting_session, barcode="00113206"))

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_patch_rejects_barcode(async_client: AsyncClient, test_section):
    response = await async_client.patch(f"/api/v2/sections/{test_section.section_id}", json={"barcode": "00113206"})

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_response_has_no_barcode(async_client: AsyncClient, test_section):
    response = await async_client.get(f"/api/v2/sections/{test_section.section_id}")

    assert response.status_code == 200, response.text
    assert "barcode" not in response.json()


@pytest.mark.asyncio
async def test_barcode_route_is_gone(async_client: AsyncClient, test_section):
    response = await async_client.get("/api/v2/sections/barcode/00113206")

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_gridtape_barcode_is_aperture_index(async_client: AsyncClient, test_cutting_session):
    await _gridtape(async_client, "GT0001")
    first = await async_client.post(
        "/api/v2/sections", json=_section(test_cutting_session, media_id="GT0001", aperture_index=int("000000"))
    )
    last = await async_client.post(
        "/api/v2/sections", json=_section(test_cutting_session, media_id="GT0001", aperture_index=int("002499"))
    )

    apertures = (await async_client.get("/api/v2/substrates/GT0001/apertures")).json()["apertures"]

    assert (first.status_code, last.status_code) == (201, 201), (first.text, last.text)
    assert apertures[0]["sections"] == [first.json()["section_id"]]
    assert apertures[2499]["sections"] == [last.json()["section_id"]]
    assert apertures[2499]["shape"]["centroid"] == [14994.0, 0.0]
    assert [apertures[i]["status"] for i in (0, 1, 2499)] == ["used", "available", "used"]


@pytest.mark.asyncio
@pytest.mark.parametrize("leader_barcode", ["100000", "200169"])
async def test_gridtape_leader_barcode_is_rejected(
    async_client: AsyncClient, test_cutting_session, leader_barcode: str
):
    await _gridtape(async_client, "GT0001")

    response = await async_client.post(
        "/api/v2/sections",
        json=_section(test_cutting_session, media_id="GT0001", aperture_index=int(leader_barcode)),
    )

    assert response.status_code == 422, response.text
    assert f"has no aperture {int(leader_barcode)}" in response.text


@pytest.mark.asyncio
async def test_same_barcode_on_two_tapes_is_two_sections(async_client: AsyncClient, test_cutting_session):
    await _gridtape(async_client, "GT0001", "GT0002")

    on_first = await async_client.post(
        "/api/v2/sections", json=_section(test_cutting_session, media_id="GT0001", aperture_index=int("000123"))
    )
    on_second = await async_client.post(
        "/api/v2/sections", json=_section(test_cutting_session, media_id="GT0002", aperture_index=int("000123"))
    )

    assert (on_first.status_code, on_second.status_code) == (201, 201), (on_first.text, on_second.text)
    assert on_first.json()["section_id"] != on_second.json()["section_id"]
