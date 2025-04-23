import pytest
from httpx import AsyncClient
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_list_substrates(async_client: AsyncClient, test_substrate):
    """Test retrieving a list of all substrates."""
    response = await async_client.get("/api/v2/substrates")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert any(sub["media_id"] == test_substrate.media_id for sub in response_data)

@pytest.mark.asyncio
async def test_list_substrates_filtered(async_client: AsyncClient, test_substrate):
    """Test retrieving substrates filtered by media_type and status."""
    response_type = await async_client.get(f"/api/v2/substrates?media_type={test_substrate.media_type}")
    assert response_type.status_code == 200
    response_type_data = response_type.json()
    assert isinstance(response_type_data, list)
    assert len(response_type_data) >= 1
    assert all(sub["media_type"] == test_substrate.media_type for sub in response_type_data)
    assert any(sub["media_id"] == test_substrate.media_id for sub in response_type_data)

    response_status = await async_client.get("/api/v2/substrates?status=new")
    assert response_status.status_code == 200
    response_status_data = response_status.json()
    assert isinstance(response_status_data, list)
    assert any(sub["media_id"] == test_substrate.media_id for sub in response_status_data if sub["status"] == "new")

@pytest.mark.asyncio
async def test_create_substrate(async_client: AsyncClient):
    """Test creating a new substrate."""
    media_id_hr = f"TEST_SUB_CREATE_{int(datetime.now(timezone.utc).timestamp())}"
    substrate_data = {
        "media_id": media_id_hr,
        "media_type": "wafer",
        "status": "new",
        "metadata": {"name": "Test Wafer Create"},
        "apertures": [{"uid": "A1", "index": 0, "status": "available"}]
    }
    response = await async_client.post("/api/v2/substrates", json=substrate_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["media_id"] == media_id_hr
    assert response_data["media_type"] == "wafer"
    assert response_data["status"] == "new"
    assert response_data["metadata"]["name"] == "Test Wafer Create"
    assert len(response_data["apertures"]) == 1
    assert response_data["apertures"][0]["uid"] == "A1"
    assert "created_at" in response_data

    await async_client.delete(f"/api/v2/substrates/{media_id_hr}")


@pytest.mark.asyncio
async def test_create_substrate_duplicate(async_client: AsyncClient, test_substrate):
    """Test attempting to create a substrate with an existing media_id."""
    substrate_data = {
        "media_id": test_substrate.media_id,
        "media_type": "grid",
        "status": "new",
    }
    response = await async_client.post("/api/v2/substrates", json=substrate_data)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_substrate(async_client: AsyncClient, test_substrate):
    """Test retrieving a specific substrate by its media_id."""
    response = await async_client.get(f"/api/v2/substrates/{test_substrate.media_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["media_id"] == test_substrate.media_id
    assert response_data["_id"] == str(test_substrate.id)
    assert response_data["media_type"] == test_substrate.media_type

@pytest.mark.asyncio
async def test_get_substrate_not_found(async_client: AsyncClient):
    """Test retrieving a non-existent substrate."""
    response = await async_client.get("/api/v2/substrates/NON_EXISTENT_SUBSTRATE")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_update_substrate(async_client: AsyncClient, test_substrate):
    """Test updating a substrate's status and metadata."""
    update_data = {
        "status": "used",
        "metadata": {"name": "Updated Test Substrate", "calibrated": datetime.now(timezone.utc).isoformat()}
        }
    response = await async_client.patch(
        f"/api/v2/substrates/{test_substrate.media_id}", json=update_data
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["status"] == "used"
    assert response_data["metadata"]["name"] == "Updated Test Substrate"
    assert "calibrated" in response_data["metadata"]
    assert response_data["media_id"] == test_substrate.media_id
    assert "updated_at" in response_data
    assert response_data["updated_at"] is not None

@pytest.mark.asyncio
async def test_delete_substrate(async_client: AsyncClient):
    """Test deleting a substrate successfully (when it has no dependencies)."""
    media_id_hr = f"TEST_SUB_DELETE_{int(datetime.now(timezone.utc).timestamp())}"
    substrate_data = {
        "media_id": media_id_hr,
        "media_type": "grid",
        "status": "new",
    }
    create_response = await async_client.post("/api/v2/substrates", json=substrate_data)
    assert create_response.status_code == 201

    delete_response = await async_client.delete(f"/api/v2/substrates/{media_id_hr}")
    assert delete_response.status_code == 204, delete_response.text

    get_response = await async_client.get(f"/api/v2/substrates/{media_id_hr}")
    assert get_response.status_code == 404

@pytest.mark.asyncio
async def test_delete_substrate_with_sections(async_client: AsyncClient, test_substrate, test_section):
    """Test that deleting a substrate fails if it has associated sections."""
    response = await async_client.delete(f"/api/v2/substrates/{test_substrate.media_id}")
    assert response.status_code == 400
    response_data = response.json()
    assert "detail" in response_data
    assert "associated sections" in response_data["detail"].lower()

@pytest.mark.asyncio
async def test_get_substrate_sections(async_client: AsyncClient, test_substrate, test_section):
    """Test retrieving sections associated with a specific substrate."""
    response = await async_client.get(f"/api/v2/substrates/{test_substrate.media_id}/sections")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    found_section = next((sec for sec in response_data if sec["section_id"] == test_section.section_id), None)
    assert found_section is not None
    assert found_section["substrate_ref"]["id"] == str(test_substrate.id)
    assert found_section["media_id"] == test_substrate.media_id
