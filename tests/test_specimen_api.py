import pytest


@pytest.mark.asyncio
async def test_list_specimens(async_client):
    response = await async_client.get("/api/v2/specimens")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_specimen(async_client):
    specimen_data = {
        "specimen_id": "TEST_CREATE_001",
        "description": "Test specimen creation",
    }
    response = await async_client.post("/api/v2/specimens", json=specimen_data)
    assert response.status_code == 200
    assert response.json()["specimen_id"] == "TEST_CREATE_001"


@pytest.mark.asyncio
async def test_get_specimen(async_client, test_specimen):
    response = await async_client.get(f"/api/v2/specimens/{test_specimen.specimen_id}")
    assert response.status_code == 200
    assert response.json()["specimen_id"] == test_specimen.specimen_id


@pytest.mark.asyncio
async def test_update_specimen(async_client, test_specimen):
    update_data = {"description": "Updated description"}
    response = await async_client.patch(
        f"/api/v2/specimens/{test_specimen.specimen_id}", json=update_data
    )
    assert response.status_code == 200
    assert response.json()["description"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_specimen(async_client, test_specimen):
    # Create a new specimen specifically for the delete test
    specimen_data = {
        "specimen_id": "TEST_DELETE_001",
        "description": "Test specimen for deletion",
    }
    create_response = await async_client.post("/api/v2/specimens", json=specimen_data)
    assert create_response.status_code == 200

    # Delete the specimen
    response = await async_client.delete(f"/api/v2/specimens/TEST_DELETE_001")
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_get_specimen_blocks(async_client, test_specimen, test_block):
    response = await async_client.get(
        f"/api/v2/specimens/{test_specimen.specimen_id}/blocks"
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_add_specimen_image(async_client, test_specimen):
    image_url = "https://example.com/test-image.jpg"
    response = await async_client.post(
        f"/api/v2/specimens/{test_specimen.specimen_id}/images",
        json={"image_url": image_url},  # Change from params to json
    )
    assert response.status_code == 200
    assert image_url in response.json()["specimen_images"]
