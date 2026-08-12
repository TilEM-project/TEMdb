import pytest
from httpx import AsyncClient


def _section_path(test_cutting_session, test_section) -> str:
    return f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}/sections/{test_section.section_id}"


@pytest.mark.asyncio
async def test_condition_lifecycle(async_client: AsyncClient, test_cutting_session, test_section):
    path = _section_path(test_cutting_session, test_section)

    created = (await async_client.get(path)).json()
    assert created["condition"] == "ok"
    assert created["destroyed"] is False

    response = await async_client.patch(path, json={"condition": "lost"})
    assert response.status_code == 200
    assert response.json()["condition"] == "lost"
    assert response.json()["destroyed"] is False

    response = await async_client.patch(path, json={"condition": "destroyed", "condition_reason": "beam damage"})
    assert response.status_code == 200
    assert response.json()["condition"] == "destroyed"
    assert response.json()["condition_reason"] == "beam damage"
    assert response.json()["destroyed"] is True


@pytest.mark.asyncio
async def test_destroyed_writes_rejected(async_client: AsyncClient, test_cutting_session, test_section):
    path = _section_path(test_cutting_session, test_section)
    response = await async_client.patch(path, json={"destroyed": True})
    assert response.status_code == 422
    assert "condition" in response.text


@pytest.mark.asyncio
async def test_invalid_condition_rejected(async_client: AsyncClient, test_cutting_session, test_section):
    path = _section_path(test_cutting_session, test_section)
    response = await async_client.patch(path, json={"condition": "broken"})
    assert response.status_code == 422
