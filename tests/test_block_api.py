import pytest


@pytest.mark.asyncio
async def test_list_blocks(async_client):
    response = await async_client.get("/api/v2/blocks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_block(async_client, test_specimen):
    block_data = {
        "block_id": "TEST_BLOCK_CREATE",
        "specimen_id": test_specimen.specimen_id,
        "microCT_info": {"resolution": 2.0},
    }
    response = await async_client.post("/api/v2/blocks", json=block_data)
    assert response.status_code == 200
    assert response.json()["block_id"] == "TEST_BLOCK_CREATE"


@pytest.mark.asyncio
async def test_get_block(async_client, test_specimen, test_block):
    response = await async_client.get(
        f"/api/v2/blocks/{test_specimen.specimen_id}/{test_block.block_id}"
    )
    assert response.status_code == 200
    assert response.json()["block_id"] == test_block.block_id


@pytest.mark.asyncio
async def test_update_block(async_client, test_specimen, test_block):
    update_data = {"microCT_info": {"resolution": 3.0}}
    response = await async_client.patch(
        f"/api/v2/blocks/{test_specimen.specimen_id}/{test_block.block_id}",
        json=update_data,
    )
    assert response.status_code == 200
    assert response.json()["microCT_info"]["resolution"] == 3.0


@pytest.mark.asyncio
async def test_delete_block(async_client, test_specimen):
    # Create a new block specifically for deletion
    block_data = {
        "block_id": "TEST_BLOCK_DELETE",
        "specimen_id": test_specimen.specimen_id,
        "microCT_info": {"resolution": 1.0},
    }
    create_response = await async_client.post("/api/v2/blocks", json=block_data)
    assert create_response.status_code == 200

    # Delete the block
    response = await async_client.delete(
        f"/api/v2/blocks/{test_specimen.specimen_id}/TEST_BLOCK_DELETE"
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_list_specimen_blocks(async_client, test_specimen):
    response = await async_client.get(
        f"/api/v2/blocks/specimens/{test_specimen.specimen_id}/blocks"
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_block_cut_sessions(
    async_client, test_specimen, test_block, test_cutting_session
):
    response = await async_client.get(
        f"/api/v2/blocks/{test_specimen.specimen_id}/{test_block.block_id}/cut-sessions"
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
