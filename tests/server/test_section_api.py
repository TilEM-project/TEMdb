import asyncio
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from temdb.models import SectionQuality
from temdb.server.api.v2.section import mark_apertures_used
from temdb.server.sqlmodels import ROISQLModel, SectionSQLModel, SubstrateSQLModel


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
async def test_create_section(async_client: AsyncClient, test_cutting_session, test_layout):
    """Test creating a new section."""

    substrate_id_hr = f"TEST_SUB_CREATE_{int(datetime.now(timezone.utc).timestamp())}"
    substrate_data = {
        "media_id": substrate_id_hr,
        "substrate_layout_id": test_layout.layout_id,
    }

    response = await async_client.post("/api/v2/substrates", json=substrate_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["media_id"] == substrate_id_hr

    section_id_hr = f"{substrate_id_hr}_S1"
    section_data = {
        "cutting_session_id": test_cutting_session.cutting_session_id,
        "timestamp": "2026-09-04T16:00:00+00:00",
        "media_id": substrate_id_hr,
        "aperture_index": 0,
        "optical_image": {"inspection": {"image_path": "http://example.com/image.png"}},
        "barcode": "BC123456789",
        "run_parameters": {"cutting_thickness_um": 45.5, "water_added": True},
    }
    response = await async_client.post("/api/v2/sections", json=section_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["section_id"] == section_id_hr
    assert response_data["cutting_session_id"] == test_cutting_session.cutting_session_id
    assert response_data["block_id"] == test_cutting_session.block_id
    assert response_data["specimen_id"] == test_cutting_session.specimen_id
    assert response_data["section_number"] == 1
    assert response_data["barcode"] == "BC123456789"
    assert response_data["run_parameters"]["cutting_thickness_um"] == 45.5
    assert response_data["run_parameters"]["water_added"] is True


@pytest.mark.asyncio
async def test_create_sections_batch(async_client: AsyncClient, test_cutting_session, test_layout):
    """Test creating multiple sections in a batch request."""
    timestamp = int(datetime.now(timezone.utc).timestamp())
    media_base = f"TEST_SUB_BATCH_{timestamp}"

    substrates_data = []
    for i in range(2):
        substrate_id = f"{media_base}_{i}"
        substrates_data.append(
            {
                "media_id": substrate_id,
                "substrate_layout_id": test_layout.layout_id,
            }
        )

    for substrate_data in substrates_data:
        substrate_response = await async_client.post("/api/v2/substrates", json=substrate_data)
        assert substrate_response.status_code == 201

    sections_data = []
    for i in range(5):
        substrate_idx = i % 2
        sections_data.append(
            {
                "cutting_session_id": test_cutting_session.cutting_session_id,
                "timestamp": f"2026-09-04T16:0{i}:00+00:00",
                "media_id": f"{media_base}_{substrate_idx}",
                "aperture_index": i % 3,
                "optical_image": {"inspection": {"image_path": f"http://example.com/image_{i}.png"}},
                "barcode": f"BATCH{timestamp}_{i}",
            }
        )

    response = await async_client.post("/api/v2/sections/batch", json=sections_data)

    assert response.status_code == 201
    created_sections = response.json()
    assert len(created_sections) == 5

    for i, section in enumerate(created_sections):
        substrate_idx = i % 2
        section_number = i // 2 + 1
        expected_section_id = f"{media_base}_{substrate_idx}_S{section_number}"

        assert section["section_id"] == expected_section_id
        assert section["cutting_session_id"] == test_cutting_session.cutting_session_id
        assert section["specimen_id"] == test_cutting_session.specimen_id
        assert section["block_id"] == test_cutting_session.block_id
        assert section["section_number"] == section_number
        assert section["media_id"] == f"{media_base}_{substrate_idx}"
        assert section["barcode"] == f"BATCH{timestamp}_{i}"

        get_path = f"/api/v2/sections/{expected_section_id}"
        get_response = await async_client.get(get_path)
        assert get_response.status_code == 200

    for i, section in enumerate(created_sections):
        delete_path = f"/api/v2/sections/{section['section_id']}"
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
            "cutting_session_id": "NON_EXISTENT_SESSION_ID",
            "timestamp": "2026-09-04T16:00:00+00:00",
            "media_id": test_substrate.media_id,
            "aperture_index": 0,
            "optical_image": {"inspection": {"image_path": "http://foobar.com/image.png"}},
        }
    ]

    response = await async_client.post("/api/v2/sections/batch", json=sections_data)
    assert response.status_code == 404
    assert "Cutting Session" in response.json()["detail"]
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_sections_batch_invalid_substrate(async_client: AsyncClient, test_cutting_session):
    """Test creating sections with an invalid substrate/media ID."""
    sections_data = [
        {
            "cutting_session_id": test_cutting_session.cutting_session_id,
            "timestamp": "2026-09-04T16:00:00+00:00",
            "media_id": "NON_EXISTENT_MEDIA_ID",
            "aperture_index": 0,
            "optical_image": {"inspection": {"image_path": "http://example.com/image.png"}},
        }
    ]

    response = await async_client.post("/api/v2/sections/batch", json=sections_data)
    assert response.status_code == 404
    assert "Substrate" in response.json()["detail"]
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_section_with_unknown_substrate_is_not_found(async_client: AsyncClient, test_cutting_session):
    section_data = {
        "cutting_session_id": test_cutting_session.cutting_session_id,
        "timestamp": "2026-09-04T16:00:00+00:00",
        "media_id": "NON_EXISTENT_MEDIA_ID",
        "aperture_index": 0,
    }

    response = await async_client.post("/api/v2/sections", json=section_data)
    assert response.status_code == 404
    assert "Substrate" in response.json()["detail"]
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_sections_batch_duplicate_placements(async_client: AsyncClient, test_cutting_session, test_layout):
    timestamp = int(datetime.now(timezone.utc).timestamp())
    media_id = f"TEST_SUB_DUP_{timestamp}"

    substrate_data = {
        "media_id": media_id,
        "substrate_layout_id": test_layout.layout_id,
    }

    substrate_response = await async_client.post("/api/v2/substrates", json=substrate_data)
    assert substrate_response.status_code == 201

    sections_data = [
        {
            "cutting_session_id": test_cutting_session.cutting_session_id,
            "timestamp": "2026-09-04T16:00:00+00:00",
            "media_id": media_id,
            "aperture_index": 0,
            "optical_image": {"inspection": {"image_path": "http://image.server.com/image1.png"}},
        },
        {
            "cutting_session_id": test_cutting_session.cutting_session_id,
            "timestamp": "2026-09-04T16:00:00+00:00",
            "media_id": media_id,
            "aperture_index": 0,
            "optical_image": {"inspection": {"image_path": "http://some.other.place.com/image2.png"}},
        },
    ]

    response = await async_client.post("/api/v2/sections/batch", json=sections_data)
    assert response.status_code == 422
    assert "more than once" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_section(async_client: AsyncClient, test_cutting_session, test_section):
    """Test retrieving a specific section by human-readable IDs."""
    path = f"/api/v2/sections/{test_section.section_id}"
    response = await async_client.get(path)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["section_id"] == test_section.section_id
    assert response_data["cutting_session_id"] == test_cutting_session.cutting_session_id
    assert response_data["id"] == test_section.id


@pytest.mark.asyncio
async def test_get_section_not_found(async_client: AsyncClient, test_cutting_session):
    """Test retrieving a non-existent section."""
    path = "/api/v2/sections/NON_EXISTENT_SECTION"
    response = await async_client.get(path)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_section(async_client: AsyncClient, test_cutting_session, test_section):
    """Test updating a section's quality."""
    update_data = {
        "section_metrics": {"quality": SectionQuality.BROKEN},
        "run_parameters": {"cut_cycle": 0.6},
        "optical_image": {"test": {"image_path": "/allen/something/something/profit.jpg"}},
    }
    path = f"/api/v2/sections/{test_section.section_id}"
    response = await async_client.patch(path, json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["section_id"] == test_section.section_id
    assert response_data["section_metrics"]["quality"] == SectionQuality.BROKEN.value
    assert response_data["run_parameters"]["cut_cycle"] == 0.6


@pytest.mark.asyncio
async def test_delete_section(async_client: AsyncClient, test_cutting_session, test_substrate):
    """Test deleting a section successfully (when it has no dependencies like ROIs)."""
    section_data = {
        "cutting_session_id": test_cutting_session.cutting_session_id,
        "timestamp": "2026-09-04T16:00:00+00:00",
        "media_id": test_substrate.media_id,
        "aperture_index": 0,
    }

    create_response = await async_client.post("/api/v2/sections", json=section_data)
    assert create_response.status_code == 201
    section_id_hr = create_response.json()["section_id"]

    delete_path = f"/api/v2/sections/{section_id_hr}"
    delete_response = await async_client.delete(delete_path)
    assert delete_response.status_code == 204

    get_response = await async_client.get(delete_path)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_section_with_rois(async_client: AsyncClient, test_section, test_roi):
    """Test that deleting a section fails if it has associated ROIs."""
    path = f"/api/v2/sections/{test_section.section_id}"
    response = await async_client.delete(path)
    assert response.status_code == 409
    response_data = response.json()
    assert response_data["error_code"] == "FOREIGN_KEY_VIOLATION"
    assert response_data["context"]["table"] == ROISQLModel.__tablename__


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


@pytest.mark.asyncio
async def test_section_on_an_aperture_the_layout_does_not_have_is_422(
    async_client: AsyncClient, test_cutting_session, test_substrate
):
    section = {
        "cutting_session_id": test_cutting_session.cutting_session_id,
        "media_id": test_substrate.media_id,
        "timestamp": "2026-09-04T16:00:00+00:00",
        "aperture_index": 3,
    }
    assert (await async_client.post("/api/v2/sections", json=section)).status_code == 422
    assert (await async_client.post("/api/v2/sections/batch", json=[section])).status_code == 422


@pytest.mark.asyncio
async def test_section_cannot_move_to_an_aperture_the_layout_does_not_have(
    async_client: AsyncClient, test_cutting_session, test_section
):
    response = await async_client.patch(
        f"/api/v2/sections/{test_section.section_id}",
        json={"aperture_index": 3},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_section_on_a_blank_has_no_aperture_and_keeps_its_position(
    async_client: AsyncClient, test_cutting_session, test_substrate
):
    response = await async_client.post(
        "/api/v2/sections",
        json={
            "cutting_session_id": test_cutting_session.cutting_session_id,
            "media_id": test_substrate.media_id,
            "timestamp": "2026-09-04T16:00:00+00:00",
            "position": {"x": 12.5, "y": -3.0},
        },
    )
    assert response.status_code == 201
    assert response.json()["aperture_index"] is None
    assert response.json()["position"] == {"x": 12.5, "y": -3.0}


@pytest.mark.asyncio
async def test_placing_a_section_marks_its_aperture_used_but_leaves_damaged_alone(
    async_client: AsyncClient, test_cutting_session, test_layout
):
    media_id = "TEST_SUB_MARKS_USED"
    created = await async_client.post(
        "/api/v2/substrates",
        json={
            "media_id": media_id,
            "substrate_layout_id": test_layout.layout_id,
            "aperture_status": ["available", "damaged", "available"],
        },
    )
    assert created.status_code == 201
    session_id = test_cutting_session.cutting_session_id

    for aperture in (0, 1):
        response = await async_client.post(
            "/api/v2/sections",
            json={
                "cutting_session_id": session_id,
                "timestamp": f"2026-09-04T16:0{aperture}:00+00:00",
                "media_id": media_id,
                "aperture_index": aperture,
            },
        )
        assert response.status_code == 201
    statuses = (await async_client.get(f"/api/v2/substrates/{media_id}")).json()["aperture_status"]
    assert statuses == ["used", "damaged", "available"]

    moved = await async_client.patch(f"/api/v2/sections/{media_id}_S1", json={"aperture_index": 2})
    assert moved.status_code == 200
    statuses = (await async_client.get(f"/api/v2/substrates/{media_id}")).json()["aperture_status"]
    assert statuses == ["used", "damaged", "used"]


@pytest.mark.asyncio
async def test_batch_marks_each_substrates_apertures_used(async_client: AsyncClient, test_cutting_session, test_layout):
    for media_id in ("TEST_SUB_BATCH_A", "TEST_SUB_BATCH_B"):
        body = {
            "media_id": media_id,
            "substrate_layout_id": test_layout.layout_id,
            "aperture_status": ["available", "damaged", "available"],
        }
        assert (await async_client.post("/api/v2/substrates", json=body)).status_code == 201
    session_id = test_cutting_session.cutting_session_id
    batch = [
        {
            "cutting_session_id": session_id,
            "timestamp": "2026-09-04T16:00:00+00:00",
            "media_id": "TEST_SUB_BATCH_A",
            "aperture_index": 0,
        },
        {
            "cutting_session_id": session_id,
            "timestamp": "2026-09-04T16:01:00+00:00",
            "media_id": "TEST_SUB_BATCH_A",
            "aperture_index": 1,
        },
        {
            "cutting_session_id": session_id,
            "timestamp": "2026-09-04T16:02:00+00:00",
            "media_id": "TEST_SUB_BATCH_B",
            "aperture_index": 2,
        },
        {"cutting_session_id": session_id, "timestamp": "2026-09-04T16:03:00+00:00", "media_id": "TEST_SUB_BATCH_B"},
    ]
    assert (await async_client.post("/api/v2/sections/batch", json=batch)).status_code == 201

    async def statuses(media_id: str) -> list[str]:
        return (await async_client.get(f"/api/v2/substrates/{media_id}")).json()["aperture_status"]

    assert await statuses("TEST_SUB_BATCH_A") == ["used", "damaged", "available"]
    assert await statuses("TEST_SUB_BATCH_B") == ["available", "damaged", "used"]


@pytest.mark.asyncio
async def test_list_sections_by_quality_pages_matches(async_client: AsyncClient, test_db_manager, test_section):
    """The quality filter applies before limit, so the page holds matching sections."""
    async with test_db_manager.async_session_factory() as session:
        broken = SectionSQLModel(
            section_id=f"{test_section.section_id}_BROKEN",
            section_number=test_section.section_number + 1,
            timestamp=test_section.timestamp,
            cutting_session_id=test_section.cutting_session_id,
            block_id=test_section.block_id,
            specimen_id=test_section.specimen_id,
            media_id=test_section.media_id,
            section_metrics={"quality": SectionQuality.BROKEN.value},
        )
        session.add(broken)
        await session.commit()

    response = await async_client.get("/api/v2/sections", params={"quality": SectionQuality.BROKEN.value, "limit": 1})
    assert [section["section_id"] for section in response.json()] == [broken.section_id]


@pytest.mark.asyncio
async def test_concurrent_section_creates_on_one_substrate_do_not_deadlock(test_db_manager, test_substrate):
    async with test_db_manager.async_session_factory() as inserting, test_db_manager.async_session_factory() as marking:
        try:
            await inserting.execute(
                select(SubstrateSQLModel.id)
                .where(SubstrateSQLModel.media_id == test_substrate.media_id)
                .with_for_update(read=True, key_share=True)
            )
            await asyncio.wait_for(mark_apertures_used(marking, test_substrate.media_id, [0]), timeout=5)
        finally:
            await inserting.rollback()
            await marking.rollback()
