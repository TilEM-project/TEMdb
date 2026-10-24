from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from temdb.server.sqlmodels import AcquisitionTaskSQLModel

drawn = datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)


def _roi(section, minutes: int = 0, payload: dict | None = None, **fields) -> dict:
    return {
        "section_id": section.section_id,
        "created_at": (drawn + timedelta(minutes=minutes)).isoformat(),
        "payload": {"vertices": [[0, 0], [10, 0], [10, 10]], "rotation_angle": 0.0, **(payload or {})},
        **fields,
    }


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
    response_sec = await async_client.get(f"/api/v2/rois?section_id={test_section.section_id}")
    assert response_sec.status_code == 200
    res_sec_data = response_sec.json()
    assert isinstance(res_sec_data, list)
    assert len(res_sec_data) >= 1
    assert all(roi["section_id"] == test_section.section_id for roi in res_sec_data)
    assert any(roi["roi_id"] == test_roi.roi_id for roi in res_sec_data)


@pytest.mark.asyncio
async def test_list_filters_parents(async_client: AsyncClient, test_roi, test_section):
    """is_parent_roi=true lists ROIs with a sub-ROI, false those without."""
    child = await async_client.post(
        "/api/v2/rois", json=_roi(test_section, minutes=5, parent_created_at=test_roi.created_at.isoformat())
    )
    assert child.status_code == 201, child.text

    parents = await async_client.get("/api/v2/rois", params={"is_parent_roi": True})
    others = await async_client.get("/api/v2/rois", params={"is_parent_roi": False})

    assert [roi["roi_id"] for roi in parents.json()] == [test_roi.roi_id]
    assert [roi["roi_id"] for roi in others.json()] == [child.json()["roi_id"]]


@pytest.mark.asyncio
async def test_create_roi(async_client: AsyncClient, test_section, test_substrate):
    """Test creating a new top-level ROI."""
    roi_data = _roi(test_section, payload={"aperture_width_height": [100, 100]})
    response = await async_client.post("/api/v2/rois", json=roi_data)
    assert response.status_code == 201
    response_data = response.json()
    assert isinstance(response_data["id"], int)
    assert response_data["roi_id"] == "SUB001.A0000.R001"
    assert response_data["section_id"] == test_section.section_id
    assert response_data["aperture_index"] == test_section.aperture_index
    assert response_data["parent_roi_id"] is None
    assert response_data["is_parent"] is False
    assert response_data["roi_payload"]["aperture_width_height"] == [100, 100]


@pytest.mark.asyncio
async def test_create_child_roi(async_client: AsyncClient, test_roi, test_section):
    """Test creating a child ROI linked to a parent."""
    child_roi_data = _roi(
        test_section, parent_created_at=test_roi.created_at.isoformat(), payload={"aperture_width_height": [50, 50]}
    )
    response = await async_client.post("/api/v2/rois", json=child_roi_data)
    assert response.status_code == 201, response.text
    response_data = response.json()
    assert response_data["roi_id"] == "SUB001.A0000.R002"
    assert response_data["section_id"] == test_roi.section_id
    assert response_data["parent_roi_id"] == test_roi.roi_id

    # The parent ROI should now report as having a child.
    parent_response = await async_client.get(f"/api/v2/rois/{test_roi.roi_id}")
    assert parent_response.status_code == 200
    assert parent_response.json()["is_parent"] is True

    await async_client.delete(f"/api/v2/rois/{response_data['roi_id']}")


@pytest.mark.asyncio
async def test_create_rois_batch(async_client: AsyncClient, test_section, test_substrate):
    """Test creating multiple ROIs in a batch request."""
    rois_data = [
        _roi(
            test_section,
            minutes=i,
            payload={
                "aperture_width_height": [100 + i * 10, 100 + i * 10],
                "aperture_centroid": [500 + i * 50, 500 + i * 50],
            },
        )
        for i in range(3)
    ]

    response = await async_client.post("/api/v2/rois/batch", json=rois_data)

    assert response.status_code == 201
    created_rois = response.json()
    assert len(created_rois) == 3

    # Verify all ROIs were created correctly
    for i, roi in enumerate(created_rois):
        assert roi["roi_id"] == f"SUB001.A0000.R{i + 1:03d}"
        assert roi["section_id"] == test_section.section_id
        assert roi["roi_payload"]["aperture_width_height"] == [100 + i * 10, 100 + i * 10]

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
async def test_create_rois_batch_invalid_section(async_client: AsyncClient, test_section):
    """Test creating ROIs with an invalid section ID."""
    rois_data = [_roi(test_section, section_id="NON_EXISTENT_SECTION_ID")]

    response = await async_client.post("/api/v2/rois/batch", json=rois_data)
    assert response.status_code == 404
    assert "NON_EXISTENT_SECTION_ID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_batch_stores_repeat_once(async_client: AsyncClient, test_section, test_substrate):
    """One ROI twice in a batch is stored once and returned for both items."""
    response = await async_client.post("/api/v2/rois/batch", json=[_roi(test_section), _roi(test_section)])

    assert response.status_code == 201, response.text
    assert [roi["roi_id"] for roi in response.json()] == ["SUB001.A0000.R001", "SUB001.A0000.R001"]


@pytest.mark.asyncio
async def test_batch_resend_reports_children(async_client: AsyncClient, test_section, test_roi):
    """A batch resending a stored ROI that has sub-ROIs returns it with is_parent true."""
    child = await async_client.post(
        "/api/v2/rois", json=_roi(test_section, minutes=5, parent_created_at=test_roi.created_at.isoformat())
    )
    assert child.status_code == 201, child.text
    resend = {
        "section_id": test_section.section_id,
        "created_at": test_roi.created_at.isoformat(),
        "payload": test_roi.roi_payload,
    }

    response = await async_client.post("/api/v2/rois/batch", json=[resend])

    assert response.status_code == 201, response.text
    assert response.json()[0]["is_parent"] is True


@pytest.mark.asyncio
async def test_get_roi(async_client: AsyncClient, test_roi):
    """Test retrieving a specific ROI by its human-readable integer ID."""
    response = await async_client.get(f"/api/v2/rois/{test_roi.roi_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["roi_id"] == test_roi.roi_id
    assert response_data["section_id"] == test_roi.section_id
    assert response_data["id"] == test_roi.id


@pytest.mark.asyncio
async def test_get_roi_not_found(async_client: AsyncClient):
    """Test retrieving a non-existent ROI."""
    response = await async_client.get(
        "/api/v2/rois/SPEC999.BLK999.CS999.SEC999.SUB999.ROI9999999"
    )  # Use hierarchical format
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_roi(async_client: AsyncClient, test_roi):
    """Test updating an ROI's attributes."""
    update_data = {"payload": {"aperture_image": "http://example.com/updated_roi.png"}}
    response = await async_client.patch(f"/api/v2/rois/{test_roi.roi_id}", json=update_data)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["roi_payload"]["aperture_image"] == "http://example.com/updated_roi.png"
    assert response_data["roi_id"] == test_roi.roi_id
    assert "updated_at" in response_data
    assert response_data["updated_at"] is not None


@pytest.mark.asyncio
async def test_update_roi_no_data(async_client: AsyncClient, test_roi):
    """Test updating an ROI with an empty payload returns 400."""
    response = await async_client.patch(f"/api/v2/rois/{test_roi.roi_id}", json={"payload": {}})
    assert response.status_code == 400
    assert "No update data provided" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_roi(async_client: AsyncClient, test_section, test_substrate):
    """Test deleting an ROI successfully (when it has no dependencies)."""
    roi_data = _roi(test_section)
    create_response = await async_client.post("/api/v2/rois", json=roi_data)
    assert create_response.status_code == 201
    created_roi_id = create_response.json()["roi_id"]

    delete_response = await async_client.delete(f"/api/v2/rois/{created_roi_id}")
    assert delete_response.status_code == 204

    get_response = await async_client.get(f"/api/v2/rois/{created_roi_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_roi_with_tasks(async_client: AsyncClient, test_roi, test_acquisition_task):
    """Test that deleting an ROI fails if it has associated acquisition tasks."""
    response = await async_client.delete(f"/api/v2/rois/{test_roi.roi_id}")
    assert response.status_code == 409
    response_data = response.json()
    assert response_data["error_code"] == "FOREIGN_KEY_VIOLATION"
    assert response_data["context"]["table"] == AcquisitionTaskSQLModel.__tablename__


@pytest.mark.asyncio
async def test_list_section_rois(async_client: AsyncClient, test_section, test_roi):
    """Test retrieving ROIs associated with a specific section."""
    response = await async_client.get(f"/api/v2/sections/{test_section.section_id}/rois")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    assert any(roi["roi_id"] == test_roi.roi_id for roi in response_data)
    assert all(roi["section_id"] == test_section.section_id for roi in response_data)


@pytest.mark.asyncio
async def test_get_child_rois(async_client: AsyncClient, test_roi, test_section):
    """Test retrieving child ROIs for a parent ROI."""
    parent_roi_id = test_roi.roi_id
    child_roi_data = _roi(test_section, parent_created_at=test_roi.created_at.isoformat())
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
    assert response_data["children"][0]["parent_roi_id"] == test_roi.roi_id
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


@pytest.mark.asyncio
async def test_roi_payload_drops_barcode(async_client: AsyncClient, test_section, test_substrate):
    roi_data = _roi(test_section, payload={"barcode": "00113206", "aperture_width_height": [100, 100]})

    response = await async_client.post("/api/v2/rois", json=roi_data)

    assert response.status_code == 201, response.text
    assert "barcode" not in response.json()["roi_payload"]
