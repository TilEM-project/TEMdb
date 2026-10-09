from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_substrates(async_client: AsyncClient, test_substrate):
    response = await async_client.get("/api/v2/substrates")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert any(sub["media_id"] == test_substrate.media_id for sub in response_data)


@pytest.mark.asyncio
async def test_list_substrates_filtered_by_layout_type(async_client: AsyncClient, test_substrate, test_layout):
    response = await async_client.get("/api/v2/substrates?media_type=tape")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert all(sub["substrate_layout_id"] == test_layout.layout_id for sub in response_data)
    assert any(sub["media_id"] == test_substrate.media_id for sub in response_data)


@pytest.mark.asyncio
async def test_create_substrate(async_client: AsyncClient, test_layout):
    media_id = f"TEST_SUB_CREATE_{int(datetime.now(timezone.utc).timestamp())}"
    response = await async_client.post(
        "/api/v2/substrates",
        json={
            "media_id": media_id,
            "substrate_layout_id": test_layout.layout_id,
            "condition": {"0": "ok"},
        },
    )
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["media_id"] == media_id
    assert response_data["substrate_layout_id"] == test_layout.layout_id
    assert response_data["condition"] == {"0": "ok"}
    assert "created_at" in response_data

    await async_client.delete(f"/api/v2/substrates/{media_id}")


@pytest.mark.asyncio
async def test_create_substrate_duplicate(async_client: AsyncClient, test_substrate):
    response = await async_client.post(
        "/api/v2/substrates",
        json={
            "media_id": test_substrate.media_id,
            "substrate_layout_id": test_substrate.substrate_layout_id,
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_substrate(async_client: AsyncClient, test_substrate):
    response = await async_client.get(f"/api/v2/substrates/{test_substrate.media_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["media_id"] == test_substrate.media_id
    assert response_data["id"] == test_substrate.id
    assert response_data["substrate_layout_id"] == test_substrate.substrate_layout_id


@pytest.mark.asyncio
async def test_get_substrate_not_found(async_client: AsyncClient):
    response = await async_client.get("/api/v2/substrates/NON_EXISTENT_SUBSTRATE")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_substrate_condition(async_client: AsyncClient, test_substrate):
    response = await async_client.patch(
        f"/api/v2/substrates/{test_substrate.media_id}",
        json={"condition": {"0": "damaged", "1": "missing"}},
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["condition"] == {"0": "damaged", "1": "missing"}
    assert response_data["media_id"] == test_substrate.media_id
    assert response_data["updated_at"] is not None


@pytest.mark.asyncio
async def test_delete_substrate(async_client: AsyncClient, test_layout):
    media_id = f"TEST_SUB_DELETE_{int(datetime.now(timezone.utc).timestamp())}"
    create_response = await async_client.post(
        "/api/v2/substrates",
        json={"media_id": media_id, "substrate_layout_id": test_layout.layout_id},
    )
    assert create_response.status_code == 201

    delete_response = await async_client.delete(f"/api/v2/substrates/{media_id}")
    assert delete_response.status_code == 204, delete_response.text

    get_response = await async_client.get(f"/api/v2/substrates/{media_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_substrate_with_sections(async_client: AsyncClient, test_substrate, test_section):
    response = await async_client.delete(f"/api/v2/substrates/{test_substrate.media_id}")
    assert response.status_code == 400
    assert "associated sections" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_substrate_sections(async_client: AsyncClient, test_substrate, test_section):
    response = await async_client.get(f"/api/v2/substrates/{test_substrate.media_id}/sections")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    found_section = next((sec for sec in response_data if sec["section_id"] == test_section.section_id), None)
    assert found_section is not None
    assert found_section["id"] == test_section.id
    assert found_section["media_id"] == test_substrate.media_id
