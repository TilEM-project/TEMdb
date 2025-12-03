import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_blocks(async_client: AsyncClient):
    """Test retrieving a list of all blocks."""
    response = await async_client.get("/api/v2/blocks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_blocks_filtered_by_specimen(async_client: AsyncClient, test_specimen, test_block):
    """Test retrieving blocks filtered by specimen ID."""
    response = await async_client.get(f"/api/v2/blocks?specimen_id={test_specimen.specimen_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    for block in response_data:
        assert block["specimen_id"] == test_specimen.specimen_id


@pytest.mark.asyncio
async def test_create_block(async_client: AsyncClient, test_specimen):
    """Test creating a new block."""
    block_id_hr = "TEST_BLOCK_CREATE_001"
    block_data = {
        "block_id": block_id_hr,
        "specimen_id": test_specimen.specimen_id,
        "microCT_info": {"resolution": 2.0, "unit": "um"},
    }
    response = await async_client.post("/api/v2/blocks", json=block_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["block_id"] == block_id_hr
    assert response_data["specimen_id"] == test_specimen.specimen_id
    assert response_data["microCT_info"] == {"resolution": 2.0, "unit": "um"}
    assert response_data["specimen_ref"]["id"] == str(test_specimen.id)

    await async_client.delete(f"/api/v2/blocks/specimens/{test_specimen.specimen_id}/blocks/{block_id_hr}")


@pytest.mark.asyncio
async def test_get_block(async_client: AsyncClient, test_specimen, test_block):
    """Test retrieving a specific block by human-readable IDs."""
    response = await async_client.get(
        f"/api/v2/blocks/specimens/{test_specimen.specimen_id}/blocks/{test_block.block_id}"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["block_id"] == test_block.block_id
    assert response_data["specimen_id"] == test_specimen.specimen_id
    assert response_data["_id"] == str(test_block.id)


@pytest.mark.asyncio
async def test_get_block_not_found(async_client: AsyncClient, test_specimen):
    """Test retrieving a non-existent block."""
    response = await async_client.get(f"/api/v2/blocks/specimens/{test_specimen.specimen_id}/blocks/NON_EXISTENT_BLOCK")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_block(async_client: AsyncClient, test_specimen, test_block):
    """Test updating a block's microCT info."""
    update_data = {"microCT_info": {"resolution": 3.5, "source": "updated"}}
    response = await async_client.patch(
        f"/api/v2/blocks/specimens/{test_specimen.specimen_id}/blocks/{test_block.block_id}",
        json=update_data,
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["microCT_info"]["resolution"] == 3.5
    assert response_data["microCT_info"]["source"] == "updated"
    assert response_data["block_id"] == test_block.block_id


@pytest.mark.asyncio
async def test_delete_block(async_client: AsyncClient, test_specimen):
    """Test deleting a block successfully (when it has no dependencies)."""
    block_id_hr = "TEST_BLOCK_DELETE_001"
    block_data = {
        "block_id": block_id_hr,
        "specimen_id": test_specimen.specimen_id,
        "microCT_info": {"resolution": 1.0},
    }
    create_response = await async_client.post("/api/v2/blocks", json=block_data)
    assert create_response.status_code == 201

    delete_response = await async_client.delete(
        f"/api/v2/blocks/specimens/{test_specimen.specimen_id}/blocks/{block_id_hr}"
    )
    assert delete_response.status_code == 204, delete_response.text

    get_response = await async_client.get(f"/api/v2/blocks/specimens/{test_specimen.specimen_id}/blocks/{block_id_hr}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_block_with_sessions(async_client: AsyncClient, test_specimen, test_block, test_cutting_session):
    """Test that deleting a block fails if it has associated cutting sessions."""
    response = await async_client.delete(
        f"/api/v2/blocks/specimens/{test_specimen.specimen_id}/blocks/{test_block.block_id}"
    )
    assert response.status_code == 400
    response_data = response.json()
    assert "detail" in response_data
    assert "associated cutting sessions" in response_data["detail"].lower()


@pytest.mark.asyncio
async def test_list_specimen_blocks(async_client: AsyncClient, test_specimen, test_block):
    """Test retrieving blocks associated with a specific specimen via path."""
    response = await async_client.get(f"/api/v2/blocks/specimens/{test_specimen.specimen_id}/blocks")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    assert response_data[0]["specimen_id"] == test_specimen.specimen_id


@pytest.mark.asyncio
async def test_get_block_cut_sessions(async_client: AsyncClient, test_specimen, test_block, test_cutting_session):
    """Test retrieving cutting sessions associated with a specific block."""
    response = await async_client.get(
        f"/api/v2/blocks/specimens/{test_specimen.specimen_id}/blocks/{test_block.block_id}/cut-sessions"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    assert response_data[0]["block_id"] == test_block.block_id
    assert response_data[0]["specimen_id"] == test_specimen.specimen_id
    assert response_data[0]["cutting_session_id"] == test_cutting_session.cutting_session_id
    # assert response_data[0]["block_ref"]["$id"] == str(test_block.id)
