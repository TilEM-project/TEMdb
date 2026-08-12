import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_specimens(async_client: AsyncClient):
    """Test retrieving a list of specimens."""
    response = await async_client.get("/api/v2/specimens")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_specimen(async_client: AsyncClient):
    """Test creating a new specimen."""
    specimen_id_hr = "TEST_CREATE_SPEC_001"
    specimen_data = {
        "specimen_id": specimen_id_hr,
        "description": "Test specimen creation",
    }
    response = await async_client.post("/api/v2/specimens", json=specimen_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["specimen_id"] == specimen_id_hr
    assert response_data["description"] == "Test specimen creation"
    assert "created_at" in response_data


@pytest.mark.asyncio
async def test_get_specimen(async_client: AsyncClient, test_specimen):
    """Test retrieving a specific specimen by its human-readable ID."""
    response = await async_client.get(f"/api/v2/specimens/{test_specimen.specimen_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["specimen_id"] == test_specimen.specimen_id
    assert response_data["id"] == test_specimen.id
    assert response_data["description"] == test_specimen.description


@pytest.mark.asyncio
async def test_get_specimen_not_found(async_client: AsyncClient):
    """Test retrieving a non-existent specimen."""
    response = await async_client.get("/api/v2/specimens/NON_EXISTENT_SPECIMEN")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_specimen(async_client: AsyncClient, test_specimen):
    """Test updating a specimen's description."""
    update_data = {"description": "Updated description for testing"}
    response = await async_client.patch(f"/api/v2/specimens/{test_specimen.specimen_id}", json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["description"] == "Updated description for testing"
    assert response_data["specimen_id"] == test_specimen.specimen_id
    assert "updated_at" in response_data
    assert response_data["updated_at"] is not None


@pytest.mark.asyncio
async def test_specimen_extra_fields_round_trip(async_client: AsyncClient):
    specimen_id_hr = "TEST_EXTRA_SPEC_001"
    create_response = await async_client.post(
        "/api/v2/specimens",
        json={
            "specimen_id": specimen_id_hr,
            "description": "Specimen with extra fields",
            "unknown_create_key": {"source": "create"},
        },
    )
    assert create_response.status_code == 201
    assert create_response.json()["unknown_create_key"] == {"source": "create"}

    patch_response = await async_client.patch(
        f"/api/v2/specimens/{specimen_id_hr}",
        json={
            "description": "Specimen patched with extra fields",
            "unknown_patch_key": ["from", "patch"],
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["unknown_patch_key"] == ["from", "patch"]

    get_response = await async_client.get(f"/api/v2/specimens/{specimen_id_hr}")
    assert get_response.status_code == 200
    assert get_response.json()["unknown_create_key"] == {"source": "create"}
    assert get_response.json()["unknown_patch_key"] == ["from", "patch"]

    list_response = await async_client.get(f"/api/v2/specimens?search={specimen_id_hr}")
    assert list_response.status_code == 200
    listed = next(spec for spec in list_response.json() if spec["specimen_id"] == specimen_id_hr)
    assert listed["unknown_create_key"] == {"source": "create"}
    assert listed["unknown_patch_key"] == ["from", "patch"]


@pytest.mark.asyncio
async def test_delete_specimen_with_blocks(async_client: AsyncClient, test_specimen, test_block):
    """Test that deleting a specimen fails if it has associated blocks."""
    response = await async_client.delete(f"/api/v2/specimens/{test_specimen.specimen_id}")
    assert response.status_code == 400  #
    response_data = response.json()
    assert "detail" in response_data
    assert "associated blocks" in response_data["detail"].lower()


@pytest.mark.asyncio
async def test_get_specimen_blocks(async_client: AsyncClient, test_specimen, test_block):
    """Test retrieving blocks associated with a specific specimen."""
    response = await async_client.get(f"/api/v2/specimens/{test_specimen.specimen_id}/blocks")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) > 0
    assert response_data[0]["specimen_id"] == test_specimen.specimen_id
    assert response_data[0]["block_id"] == test_block.block_id
    assert response_data[0]["id"] == test_block.id


@pytest.mark.asyncio
async def test_add_specimen_image(async_client: AsyncClient, test_specimen):
    """Test adding an image URL to a specimen."""
    image_url = "https://example.com/test-image-for-add.jpg"
    response = await async_client.post(
        f"/api/v2/specimens/{test_specimen.specimen_id}/images",
        json={"image_url": image_url},
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "specimen_images" in response_data
    assert image_url in response_data["specimen_images"]


@pytest.mark.asyncio
async def test_remove_specimen_image(async_client: AsyncClient, test_specimen):
    """Test removing an image URL from a specimen."""
    image_url_to_add_remove = "https://example.com/test-image-for-remove.jpg"

    add_response = await async_client.post(
        f"/api/v2/specimens/{test_specimen.specimen_id}/images",
        json={"image_url": image_url_to_add_remove},
    )
    assert add_response.status_code == 200
    assert image_url_to_add_remove in add_response.json()["specimen_images"]
    remove_response = await async_client.delete(
        f"/api/v2/specimens/{test_specimen.specimen_id}/images?image_url={image_url_to_add_remove}"
    )
    assert remove_response.status_code == 200
    response_data = remove_response.json()
    assert "specimen_images" in response_data
    assert image_url_to_add_remove not in response_data["specimen_images"]
