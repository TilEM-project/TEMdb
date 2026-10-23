import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_a_section_is_read_by_its_section_id_alone(async_client: AsyncClient, test_section):
    response = await async_client.get(f"/api/v2/sections/{test_section.section_id}")

    assert response.status_code == 200, response.text
    assert response.json()["section_id"] == test_section.section_id


@pytest.mark.asyncio
async def test_a_section_is_updated_by_its_section_id_alone(async_client: AsyncClient, test_section):
    response = await async_client.patch(f"/api/v2/sections/{test_section.section_id}", json={"barcode": "BC2"})

    assert response.status_code == 200, response.text
    assert response.json()["barcode"] == "BC2"


@pytest.mark.asyncio
async def test_a_section_is_deleted_by_its_section_id_alone(async_client: AsyncClient, test_section):
    deleted = await async_client.delete(f"/api/v2/sections/{test_section.section_id}")
    read = await async_client.get(f"/api/v2/sections/{test_section.section_id}")

    assert (deleted.status_code, read.status_code) == (204, 404)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_an_unknown_section_id_is_404(async_client: AsyncClient, test_section, method: str):
    body = {"barcode": "BC2"} if method == "PATCH" else None

    response = await async_client.request(method, "/api/v2/sections/NO_SUCH_SECTION", json=body)

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
async def test_the_cutting_session_routes_for_one_section_are_gone(
    async_client: AsyncClient, test_cutting_session, test_section, method: str
):
    body = {"barcode": "BC2"} if method == "PATCH" else None
    path = f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}/sections/{test_section.section_id}"

    response = await async_client.request(method, path, json=body)

    assert response.status_code in (404, 405), response.text
