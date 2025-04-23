import pytest
from httpx import AsyncClient
from datetime import datetime, timezone


from temdb.models.v2.enum_schemas import SectionQuality


@pytest.mark.asyncio
async def test_list_sections_unfiltered(async_client: AsyncClient):
    """Test retrieving a list of all sections."""
    response = await async_client.get("/api/v2/sections")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_sections_filtered(
    async_client: AsyncClient,
    test_specimen,
    test_block,
    test_cutting_session,
    test_section,
):
    """Test filtering sections by various criteria."""
    response_spec = await async_client.get(
        f"/api/v2/sections?specimen_id={test_specimen.specimen_id}"
    )
    assert response_spec.status_code == 200
    assert all(
        s["specimen_id"] == test_specimen.specimen_id for s in response_spec.json()
    )
    assert any(s["section_id"] == test_section.section_id for s in response_spec.json())

    response_block = await async_client.get(
        f"/api/v2/sections?block_id={test_block.block_id}"
    )
    assert response_block.status_code == 200
    assert all(s["block_id"] == test_block.block_id for s in response_block.json())
    assert any(
        s["section_id"] == test_section.section_id for s in response_block.json()
    )

    response_session = await async_client.get(
        f"/api/v2/sections?cutting_session_id={test_cutting_session.cutting_session_id}"
    )
    assert response_session.status_code == 200
    assert all(
        s["cutting_session_id"] == test_cutting_session.cutting_session_id
        for s in response_session.json()
    )
    assert any(
        s["section_id"] == test_section.section_id for s in response_session.json()
    )

    response_media = await async_client.get(
        f"/api/v2/sections?media_id={test_section.media_id}"
    )
    assert response_media.status_code == 200
    assert all(
        s["media_id"] == test_section.media_id
        for s in response_media.json()
    )
    assert any(
        s["section_id"] == test_section.section_id for s in response_media.json()
    )


@pytest.mark.asyncio
async def test_create_section(async_client: AsyncClient, test_cutting_session):
    """Test creating a new section."""

    substrate_id_hr = f"TEST_SUB_CREATE_{int(datetime.now(timezone.utc).timestamp())}"
    substrate_data = {
        "media_id": substrate_id_hr,
        "media_type": "wafer",
        "status": "new",
        "metadata": {"name": "Test Wafer Create"},
        "apertures": [{"uid": "A1", "index": 0, "status": "available"}],
    }

    response = await async_client.post("/api/v2/substrates", json=substrate_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["media_id"] == substrate_id_hr

    section_id_hr = f"TEST_SUB_CREATE_{int(datetime.now(timezone.utc).timestamp())}_S99"
    section_data = {
        "specimen_id": test_cutting_session.specimen_id,
        "block_id": test_cutting_session.block_id,
        "cutting_session_id": test_cutting_session.cutting_session_id,
        "section_number": 99,
        "media_id": substrate_id_hr,
        "optical_image": {"url": "http://example.com/image.png"},
        "barcode": "BC123456789",
    }
    response = await async_client.post("/api/v2/sections", json=section_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["section_id"] == section_id_hr
    assert (
        response_data["cutting_session_id"] == test_cutting_session.cutting_session_id
    )
    assert response_data["block_id"] == test_cutting_session.block_id
    assert response_data["specimen_id"] == test_cutting_session.specimen_id
    assert response_data["section_number"] == 99
    assert response_data["barcode"] == "BC123456789"


@pytest.mark.asyncio
async def test_get_section(
    async_client: AsyncClient, test_cutting_session, test_section
):
    """Test retrieving a specific section by human-readable IDs."""
    path = f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}/sections/{test_section.section_id}"
    response = await async_client.get(path)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["section_id"] == test_section.section_id
    assert (
        response_data["cutting_session_id"] == test_cutting_session.cutting_session_id
    )
    assert response_data["_id"] == str(test_section.id)


@pytest.mark.asyncio
async def test_get_section_not_found(async_client: AsyncClient, test_cutting_session):
    """Test retrieving a non-existent section."""
    path = f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}/sections/NON_EXISTENT_SECTION"
    response = await async_client.get(path)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_section(
    async_client: AsyncClient, test_cutting_session, test_section
):
    """Test updating a section's quality."""
    update_data = {"section_metrics": {"quality": SectionQuality.BROKEN}}
    path = f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}/sections/{test_section.section_id}"
    response = await async_client.patch(path, json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["section_id"] == test_section.section_id
    assert response_data["section_metrics"]["quality"] == SectionQuality.BROKEN.value


@pytest.mark.asyncio
async def test_delete_section(async_client: AsyncClient, test_cutting_session):
    """Test deleting a section successfully (when it has no dependencies like ROIs)."""
    section_data = {
        "specimen_id": test_cutting_session.specimen_id,
        "block_id": test_cutting_session.block_id,
        "cutting_session_id": test_cutting_session.cutting_session_id,
        "section_number": 100,
        "media_type": "tape",
        "media_id": "TAPE_TEST_DELETE_01",
    }

    section_id_hr = "TAPE_TEST_DELETE_01_S100"
    create_response = await async_client.post("/api/v2/sections", json=section_data)
    assert create_response.status_code == 201

    delete_path = f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}/sections/{section_id_hr}"
    delete_response = await async_client.delete(delete_path)
    assert delete_response.status_code == 204

    get_response = await async_client.get(delete_path)
    assert get_response.status_code == 404


# @pytest.mark.asyncio
# async def test_delete_section_with_rois(async_client: AsyncClient, test_cutting_session, test_section, test_roi):
#     """Test that deleting a section fails if it has associated ROIs."""
#     # test_roi fixture should be linked to test_section via conftest update
#     path = f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}/sections/{test_section.section_id}"
#     response = await async_client.delete(path)
#     assert response.status_code == 400 # Expect Bad Request
#     response_data = response.json()
#     assert "detail" in response_data
#     assert "associated ROIs" in response_data["detail"].lower() # Check message


@pytest.mark.asyncio
async def test_list_cutting_session_sections(
    async_client: AsyncClient, test_cutting_session, test_section
):
    """Test retrieving sections via the simplified session path."""
    path = f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}"
    response = await async_client.get(path)
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    assert any(s["section_id"] == test_section.section_id for s in response_data)
    assert all(
        s["cutting_session_id"] == test_cutting_session.cutting_session_id
        for s in response_data
    )


@pytest.mark.asyncio
async def test_list_block_sections(async_client: AsyncClient, test_block, test_section):
    """Test retrieving sections via the simplified block path."""
    path = f"/api/v2/sections/blocks/{test_block.block_id}"
    response = await async_client.get(path)
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    assert any(s["section_id"] == test_section.section_id for s in response_data)
    assert all(s["block_id"] == test_block.block_id for s in response_data)


@pytest.mark.asyncio
async def test_list_specimen_sections(
    async_client: AsyncClient, test_specimen, test_section
):
    """Test retrieving sections via the simplified specimen path."""
    path = f"/api/v2/sections/specimens/{test_specimen.specimen_id}"
    response = await async_client.get(path)
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    assert any(s["section_id"] == test_section.section_id for s in response_data)
    assert all(s["specimen_id"] == test_specimen.specimen_id for s in response_data)


@pytest.mark.asyncio
async def test_list_sections_by_media(async_client: AsyncClient, test_section):
    """Test retrieving sections by media ID."""
    path = f"/api/v2/sections/media/{test_section.media_id}"
    response = await async_client.get(path)
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    assert any(s["section_id"] == test_section.section_id for s in response_data)
    assert all(
        s["media_id"] == test_section.media_id
        for s in response_data
    )


# @pytest.mark.asyncio
# async def test_get_sections_by_barcode(async_client: AsyncClient, test_section):
#     """Test retrieving sections by barcode."""
#     if not test_section.barcode:
#         pytest.skip("Test section fixture does not have a barcode")
#     path = f"/api/v2/sections/barcode/{test_section.barcode}"
#     response = await async_client.get(path)
#     assert response.status_code == 200
#     response_data = response.json()
#     assert isinstance(response_data, list)
#     assert len(response_data) >= 1
#     assert any(s["section_id"] == test_section.section_id for s in response_data)
#     assert all(s["barcode"] == test_section.barcode for s in response_data)
