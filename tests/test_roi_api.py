import pytest
from httpx import AsyncClient
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_list_rois_unfiltered(async_client: AsyncClient):
    """Test retrieving a list of all ROIs."""
    response = await async_client.get("/api/v2/rois")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_rois_filtered(
    async_client: AsyncClient,
    test_specimen,
    test_block,
    test_cutting_session,
    test_section,
    test_roi,
):
    """Test filtering ROIs by parent IDs."""
    response_sec = await async_client.get(
        f"/api/v2/rois?section_id={test_section.section_id}"
    )
    assert response_sec.status_code == 200
    res_sec_data = response_sec.json()
    assert isinstance(res_sec_data, list)
    assert len(res_sec_data) >= 1
    assert all(roi["section_id"] == test_section.section_id for roi in res_sec_data)
    assert any(roi["roi_id"] == test_roi.roi_id for roi in res_sec_data)


@pytest.mark.asyncio
async def test_create_roi(async_client: AsyncClient, test_section, test_substrate):
    """Test creating a new top-level ROI."""
    roi_data = {
        "roi_number": 9001,
        "section_id": test_section.section_id,
        "aperture_width_height": [100, 100],
        "specimen_id": test_section.specimen_id,
        "block_id": test_section.block_id,
        "substrate_media_id": test_substrate.media_id,
        "section_number": test_section.section_number,
    }
    response = await async_client.post("/api/v2/rois", json=roi_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["roi_id"].endswith("ROI9001")  # Check hierarchical ID format
    assert response_data["section_id"] == test_section.section_id
    assert response_data["block_id"] == test_section.block_id
    assert response_data["specimen_id"] == test_section.specimen_id
    assert response_data["parent_roi_ref"] is None


@pytest.mark.asyncio
async def test_create_child_roi(async_client: AsyncClient, test_roi, test_substrate):
    """Test creating a child ROI linked to a parent."""
    child_roi_data = {
        "roi_number": 1,
        "section_id": test_roi.section_id,
        "parent_roi_id": test_roi.roi_id,
        "aperture_width_height": [50, 50],
        "specimen_id": test_roi.specimen_id,
        "block_id": test_roi.block_id,
        "substrate_media_id": test_substrate.media_id,
    }
    response = await async_client.post("/api/v2/rois", json=child_roi_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["roi_id"].startswith(test_roi.roi_id)  # Should extend parent ID
    assert response_data["section_id"] == test_roi.section_id
    assert "parent_roi_ref" in response_data
    assert response_data["parent_roi_ref"]["id"] == str(test_roi.id)


@pytest.mark.asyncio
async def test_create_rois_batch(async_client: AsyncClient, test_section, test_substrate):
    """Test creating multiple ROIs in a batch request."""
    rois_data = [
        {
            "roi_number": 8000 + i,
            "section_id": test_section.section_id,
            "specimen_id": test_section.specimen_id,
            "block_id": test_section.block_id,
            "substrate_media_id": test_substrate.media_id,
            "section_number": test_section.section_number,
            "aperture_width_height": [100 + i * 10, 100 + i * 10],
            "aperture_centroid": [500 + i * 50, 500 + i * 50],
        }
        for i in range(3)
    ]

    response = await async_client.post("/api/v2/rois/batch", json=rois_data)

    assert response.status_code == 201
    created_rois = response.json()
    assert len(created_rois) == 3

    # Verify all ROIs were created correctly
    for i, roi in enumerate(created_rois):
        assert roi["roi_id"].endswith(f"ROI{8000 + i}")  # Check hierarchical ID format
        assert roi["section_id"] == test_section.section_id
        assert roi["specimen_id"] == test_section.specimen_id
        assert roi["block_id"] == test_section.block_id

    # Test retrieving created ROIs and clean up
    for roi in created_rois:
        get_response = await async_client.get(f"/api/v2/rois/{roi['roi_id']}")
        assert get_response.status_code == 200
        await async_client.delete(f"/api/v2/rois/{roi['roi_id']}")


@pytest.mark.asyncio
async def test_create_rois_batch_empty(async_client: AsyncClient):
    """Test creating an empty batch of ROIs returns 400."""
    response = await async_client.post("/api/v2/rois/batch", json=[])
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_rois_batch_invalid_section(async_client: AsyncClient):
    """Test creating ROIs with an invalid section ID."""
    rois_data = [
        {
            "roi_number": 8500,
            "section_id": "NON_EXISTENT_SECTION_ID",
            "specimen_id": "test_specimen",
            "block_id": "test_block",
            "substrate_media_id": "SUB001",
            "section_number": 1,
            "aperture_width_height": [100, 100],
        }
    ]

    response = await async_client.post("/api/v2/rois/batch", json=rois_data)
    assert response.status_code == 404
    assert "not found for ROI item" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_rois_batch_duplicate_ids(async_client: AsyncClient, test_section, test_substrate):
    """Test creating ROIs with duplicate IDs in the same batch."""
    rois_data = [
        {
            "roi_number": 9500,
            "section_id": test_section.section_id,
            "specimen_id": test_section.specimen_id,
            "block_id": test_section.block_id,
            "substrate_media_id": test_substrate.media_id,
            "section_number": test_section.section_number,
            "aperture_width_height": [100, 100],
        },
        {
            "roi_number": 9500,
            "section_id": test_section.section_id,
            "specimen_id": test_section.specimen_id,
            "block_id": test_section.block_id,
            "substrate_media_id": test_substrate.media_id,
            "section_number": test_section.section_number,
            "aperture_width_height": [200, 200],
        },
    ]

    response = await async_client.post("/api/v2/rois/batch", json=rois_data)
    assert response.status_code == 409
    assert "duplicate" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_roi(async_client: AsyncClient, test_roi):
    """Test retrieving a specific ROI by its human-readable integer ID."""
    response = await async_client.get(f"/api/v2/rois/{test_roi.roi_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["roi_id"] == test_roi.roi_id
    assert response_data["section_id"] == test_roi.section_id
    assert response_data["_id"] == str(test_roi.id)


@pytest.mark.asyncio
async def test_get_roi_not_found(async_client: AsyncClient):
    """Test retrieving a non-existent ROI."""
    response = await async_client.get("/api/v2/rois/SPEC999.BLK999.CS999.SEC999.SUB999.ROI9999999")  # Use hierarchical format
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_roi(async_client: AsyncClient, test_roi):
    """Test updating an ROI's attributes."""
    update_data = {"aperture_image": "http://example.com/updated_roi.png"}
    response = await async_client.patch(
        f"/api/v2/rois/{test_roi.roi_id}", json=update_data
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["aperture_image"] == "http://example.com/updated_roi.png"
    assert response_data["roi_id"] == test_roi.roi_id
    assert "updated_at" in response_data
    assert response_data["updated_at"] is not None


@pytest.mark.asyncio
async def test_delete_roi(async_client: AsyncClient, test_section, test_substrate):
    """Test deleting an ROI successfully (when it has no dependencies)."""
    roi_data = {
        "roi_number": 9002,
        "section_id": test_section.section_id,
        "specimen_id": test_section.specimen_id,
        "block_id": test_section.block_id,
        "substrate_media_id": test_substrate.media_id,
        "section_number": test_section.section_number,
    }
    create_response = await async_client.post("/api/v2/rois", json=roi_data)
    assert create_response.status_code == 201
    created_roi_id = create_response.json()["roi_id"]

    delete_response = await async_client.delete(f"/api/v2/rois/{created_roi_id}")
    assert delete_response.status_code == 204

    get_response = await async_client.get(f"/api/v2/rois/{created_roi_id}")
    assert get_response.status_code == 404


# @pytest.mark.asyncio
# async def test_delete_roi_with_children(async_client: AsyncClient, test_roi):
#     """Test deleting an ROI fails if it has child ROIs."""
#     # 1. Create a child ROI linked to test_roi
#     child_roi_id_hr = test_roi.roi_id + 1
#     child_roi_data = {
#         "roi_id": child_roi_id_hr, "section_id": test_roi.section_id,
#         "parent_roi_id": test_roi.roi_id, "specimen_id": test_roi.specimen_id,
#         "block_id": test_roi.block_id, "section_number": test_roi.section_number
#     }
#     cr_resp = await async_client.post("/api/v2/rois", json=child_roi_data)
#     assert cr_resp.status_code == 201

#     # 2. Attempt to delete the parent ROI (test_roi)
#     response = await async_client.delete(f"/api/v2/rois/{test_roi.roi_id}")
#     assert response.status_code == 400
#     assert "child ROIs" in response.json()["detail"].lower()

#     # Cleanup child
#     await async_client.delete(f"/api/v2/rois/{child_roi_id_hr}")


# @pytest.mark.asyncio
# async def test_delete_roi_with_tasks(async_client: AsyncClient, test_roi, test_acquisition_task):
#     """Test deleting an ROI fails if it has associated AcquisitionTasks."""
#     # test_acquisition_task fixture links to test_roi
#     response = await async_client.delete(f"/api/v2/rois/{test_roi.roi_id}")
#     assert response.status_code == 400
#     assert "associated Acquisition Tasks" in response.json()["detail"].lower()


# @pytest.mark.asyncio
# async def test_delete_roi_with_acquisitions(async_client: AsyncClient, test_roi, test_acquisition):
#     """Test deleting an ROI fails if it has associated Acquisitions."""
#     # test_acquisition fixture links to test_roi
#     response = await async_client.delete(f"/api/v2/rois/{test_roi.roi_id}")
#     assert response.status_code == 400
#     assert "associated Acquisitions" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_section_rois(async_client: AsyncClient, test_section, test_roi):
    """Test retrieving ROIs associated with a specific section."""
    response = await async_client.get(
        f"/api/v2/sections/{test_section.section_id}/rois"
    )
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    assert any(roi["roi_id"] == test_roi.roi_id for roi in response_data)
    assert all(roi["section_id"] == test_section.section_id for roi in response_data)


@pytest.mark.asyncio
async def test_get_child_rois(async_client: AsyncClient, test_roi, test_substrate):
    """Test retrieving child ROIs for a parent ROI."""
    parent_roi_id = test_roi.roi_id
    child_roi_data = {
        "roi_number": 1,
        "section_id": test_roi.section_id,
        "parent_roi_id": parent_roi_id,
        "specimen_id": test_roi.specimen_id,
        "block_id": test_roi.block_id,
        "substrate_media_id": test_substrate.media_id,
    }
    cr_resp = await async_client.post("/api/v2/rois", json=child_roi_data)
    assert cr_resp.status_code == 201
    child_roi_id = cr_resp.json()["roi_id"]

    response = await async_client.get(f"/api/v2/rois/{parent_roi_id}/children")
    assert response.status_code == 200
    response_data = response.json()
    assert "children" in response_data
    assert "metadata" in response_data
    assert isinstance(response_data["children"], list)
    assert len(response_data["children"]) == 1
    assert response_data["children"][0]["roi_id"] == child_roi_id
    assert response_data["children"][0]["parent_roi_ref"]["id"] == str(test_roi.id)
    assert response_data["metadata"]["total_children"] == 1

    await async_client.delete(f"/api/v2/rois/{child_roi_id}")


@pytest.mark.asyncio
async def test_get_child_rois_no_children(async_client: AsyncClient, test_roi):
    """Test retrieving children for an ROI that has none."""
    response = await async_client.get(f"/api/v2/rois/{test_roi.roi_id}/children")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data["children"], list)
    assert len(response_data["children"]) == 0
    assert response_data["metadata"]["total_children"] == 0
