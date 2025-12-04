from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from temdb.models import SectionQuality


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
    response_spec = await async_client.get(f"/api/v2/sections?specimen_id={test_specimen.specimen_id}")
    assert response_spec.status_code == 200
    assert all(s["specimen_id"] == test_specimen.specimen_id for s in response_spec.json())
    assert any(s["section_id"] == test_section.section_id for s in response_spec.json())

    response_block = await async_client.get(f"/api/v2/sections?block_id={test_block.block_id}")
    assert response_block.status_code == 200
    assert all(s["block_id"] == test_block.block_id for s in response_block.json())
    assert any(s["section_id"] == test_section.section_id for s in response_block.json())

    response_session = await async_client.get(
        f"/api/v2/sections?cutting_session_id={test_cutting_session.cutting_session_id}"
    )
    assert response_session.status_code == 200
    assert all(s["cutting_session_id"] == test_cutting_session.cutting_session_id for s in response_session.json())
    assert any(s["section_id"] == test_section.section_id for s in response_session.json())

    response_media = await async_client.get(f"/api/v2/sections?media_id={test_section.media_id}")
    assert response_media.status_code == 200
    assert all(s["media_id"] == test_section.media_id for s in response_media.json())
    assert any(s["section_id"] == test_section.section_id for s in response_media.json())


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
    assert response_data["cutting_session_id"] == test_cutting_session.cutting_session_id
    assert response_data["block_id"] == test_cutting_session.block_id
    assert response_data["specimen_id"] == test_cutting_session.specimen_id
    assert response_data["section_number"] == 99
    assert response_data["barcode"] == "BC123456789"


@pytest.mark.asyncio
async def test_create_sections_batch(async_client: AsyncClient, test_cutting_session):
    """Test creating multiple sections in a batch request."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    media_base = f"TEST_SUB_BATCH_{timestamp}"

    substrates_data = []
    for i in range(2):
        substrate_id = f"{media_base}_{i}"
        substrates_data.append(
            {
                "media_id": substrate_id,
                "media_type": test_cutting_session.media_type,
                "status": "new",
                "uid": f"SUBSTRATE_{i}",
                "metadata": {"name": f"Test Substrate Batch {i}"},
                "apertures": [{"uid": f"A{j}", "index": j, "status": "available"} for j in range(3)],
            }
        )

    for substrate_data in substrates_data:
        substrate_response = await async_client.post("/api/v2/substrates", json=substrate_data)
        assert substrate_response.status_code == 201

    sections_data = []
    for i in range(5):
        substrate_idx = i % 2
        section_number = i + 1
        sections_data.append(
            {
                "specimen_id": test_cutting_session.specimen_id,
                "block_id": test_cutting_session.block_id,
                "cutting_session_id": test_cutting_session.cutting_session_id,
                "section_number": section_number,
                "media_id": f"{media_base}_{substrate_idx}",
                "optical_image": {"url": f"http://example.com/image_{i}.png"},
                "barcode": f"BATCH{timestamp}_{i}",
            }
        )

    response = await async_client.post("/api/v2/sections/batch", json=sections_data)

    assert response.status_code == 201
    created_sections = response.json()
    assert len(created_sections) == 5

    for i, section in enumerate(created_sections):
        substrate_idx = i % 2
        section_number = i + 1
        expected_section_id = f"{media_base}_{substrate_idx}_S{section_number:05d}"

        assert section["section_id"] == expected_section_id
        assert section["cutting_session_id"] == test_cutting_session.cutting_session_id
        assert section["specimen_id"] == test_cutting_session.specimen_id
        assert section["block_id"] == test_cutting_session.block_id
        assert section["section_number"] == section_number
        assert section["media_id"] == f"{media_base}_{substrate_idx}"
        assert section["barcode"] == f"BATCH{timestamp}_{i}"

        session_id = test_cutting_session.cutting_session_id
        get_path = f"/api/v2/sections/sessions/{session_id}/sections/{expected_section_id}"
        get_response = await async_client.get(get_path)
        assert get_response.status_code == 200

    for i, section in enumerate(created_sections):
        session_id = test_cutting_session.cutting_session_id
        delete_path = f"/api/v2/sections/sessions/{session_id}/sections/{section['section_id']}"
        await async_client.delete(delete_path)


@pytest.mark.asyncio
async def test_create_sections_batch_empty(async_client: AsyncClient):
    """Test creating an empty batch of sections returns 400."""
    response = await async_client.post("/api/v2/sections/batch", json=[])
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_sections_batch_invalid_session(async_client: AsyncClient, test_substrate):
    """Test creating sections with an invalid cutting session ID."""
    sections_data = [
        {
            "specimen_id": "test_specimen",
            "block_id": "test_block",
            "cutting_session_id": "NON_EXISTENT_SESSION_ID",
            "section_number": 1,
            "media_id": test_substrate.media_id,
            "optical_image": {"url": "http://foobar.com/image.png"},
        }
    ]

    response = await async_client.post("/api/v2/sections/batch", json=sections_data)
    assert response.status_code == 404
    assert "CuttingSession" in response.json()["detail"]
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_sections_batch_invalid_substrate(async_client: AsyncClient, test_cutting_session):
    """Test creating sections with an invalid substrate/media ID."""
    sections_data = [
        {
            "specimen_id": test_cutting_session.specimen_id,
            "block_id": test_cutting_session.block_id,
            "cutting_session_id": test_cutting_session.cutting_session_id,
            "section_number": 1,
            "media_id": "NON_EXISTENT_MEDIA_ID",
            "optical_image": {"url": "http://example.com/image.png"},
        }
    ]

    response = await async_client.post("/api/v2/sections/batch", json=sections_data)
    assert response.status_code == 404
    assert "Substrate" in response.json()["detail"]
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_sections_batch_duplicate_ids(async_client: AsyncClient, test_cutting_session):
    """Test creating sections with duplicate IDs in the same batch."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    media_id = f"TEST_SUB_DUP_{timestamp}"

    substrate_data = {
        "media_id": media_id,
        "media_type": test_cutting_session.media_type,
        "status": "new",
        "metadata": {"name": "Test Substrate Duplicate"},
        "apertures": [{"uid": "A1", "index": 0, "status": "available"}],
    }

    substrate_response = await async_client.post("/api/v2/substrates", json=substrate_data)
    assert substrate_response.status_code == 201

    sections_data = [
        {
            "specimen_id": test_cutting_session.specimen_id,
            "block_id": test_cutting_session.block_id,
            "cutting_session_id": test_cutting_session.cutting_session_id,
            "section_number": 1,
            "media_id": media_id,
            "optical_image": {"url": "http://image.server.com/image1.png"},
        },
        {
            "specimen_id": test_cutting_session.specimen_id,
            "block_id": test_cutting_session.block_id,
            "cutting_session_id": test_cutting_session.cutting_session_id,
            "section_number": 1,
            "media_id": media_id,
            "optical_image": {"url": "http://some.other.place.com/image2.png"},
        },
    ]

    response = await async_client.post("/api/v2/sections/batch", json=sections_data)
    assert response.status_code == 409
    assert "duplicate" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_section(async_client: AsyncClient, test_cutting_session, test_section):
    """Test retrieving a specific section by human-readable IDs."""
    path = f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}/sections/{test_section.section_id}"
    response = await async_client.get(path)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["section_id"] == test_section.section_id
    assert response_data["cutting_session_id"] == test_cutting_session.cutting_session_id
    assert response_data["_id"] == str(test_section.id)


@pytest.mark.asyncio
async def test_get_section_not_found(async_client: AsyncClient, test_cutting_session):
    """Test retrieving a non-existent section."""
    path = f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}/sections/NON_EXISTENT_SECTION"
    response = await async_client.get(path)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_section(async_client: AsyncClient, test_cutting_session, test_section):
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
async def test_list_cutting_session_sections(async_client: AsyncClient, test_cutting_session, test_section):
    """Test retrieving sections via the simplified session path."""
    path = f"/api/v2/sections/sessions/{test_cutting_session.cutting_session_id}"
    response = await async_client.get(path)
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    assert any(s["section_id"] == test_section.section_id for s in response_data)
    assert all(s["cutting_session_id"] == test_cutting_session.cutting_session_id for s in response_data)


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
async def test_list_specimen_sections(async_client: AsyncClient, test_specimen, test_section):
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
    assert all(s["media_id"] == test_section.media_id for s in response_data)


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
