from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from temdb.models import AcquisitionStatus
from temdb.server.documents import AcquisitionDocument


@pytest.fixture
async def lens_correction_acquisition(init_db, test_specimen, test_roi, test_acquisition_task):
    """Create a lens correction acquisition."""
    lc = AcquisitionDocument(
        acquisition_id="LC_001",
        montage_id="LC_MONTAGE_001",
        specimen_id=test_specimen.specimen_id,
        roi_id=test_roi.roi_id,
        acquisition_task_id=test_acquisition_task.task_id,
        specimen_ref=test_specimen.id,
        roi_ref=test_roi.id,
        acquisition_task_ref=test_acquisition_task.id,
        hardware_settings={
            "scope_id": "TEM1",
            "camera_model": "Test Camera",
            "camera_serial": "12345",
            "camera_bit_depth": 16,
            "media_type": "tape",
        },
        acquisition_settings={
            "magnification": 2000,
            "spot_size": 3,
            "exposure_time": 100,
            "tile_size": [4096, 4096],
            "tile_overlap": 0.6,
            "saved_bit_depth": 8,
        },
        lens_correction=True,
        tilt_angle=0.0,
        status=AcquisitionStatus.ACQUIRED,
        start_time=datetime.now(timezone.utc),
    )
    await lc.insert()
    yield lc


@pytest.fixture
async def acquisition_with_lc(init_db, test_specimen, test_roi, test_acquisition_task, lens_correction_acquisition):
    """Create an acquisition that uses the lens correction."""
    acq = AcquisitionDocument(
        acquisition_id="ACQ_WITH_LC_001",
        montage_id="MONTAGE_WITH_LC_001",
        specimen_id=test_specimen.specimen_id,
        roi_id=test_roi.roi_id,
        acquisition_task_id=test_acquisition_task.task_id,
        specimen_ref=test_specimen.id,
        roi_ref=test_roi.id,
        acquisition_task_ref=test_acquisition_task.id,
        hardware_settings={
            "scope_id": "TEM1",
            "camera_model": "Test Camera",
            "camera_serial": "12345",
            "camera_bit_depth": 16,
            "media_type": "tape",
        },
        acquisition_settings={
            "magnification": 2000,
            "spot_size": 3,
            "exposure_time": 100,
            "tile_size": [4096, 4096],
            "tile_overlap": 0.1,
            "saved_bit_depth": 8,
        },
        lens_correction=False,
        lens_correction_acquisition_id=lens_correction_acquisition.acquisition_id,
        tilt_angle=0.0,
        status=AcquisitionStatus.IMAGING,
        start_time=datetime.now(timezone.utc),
    )
    await acq.insert()
    yield acq


@pytest.mark.asyncio
async def test_get_current_lens_correction(async_client: AsyncClient, lens_correction_acquisition):
    """Test getting current lens correction for scope and magnification."""
    response = await async_client.get(
        "/api/v2/lens-corrections/current",
        params={
            "scope_id": "TEM1",
            "magnification": 2000,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["acquisition_id"] == lens_correction_acquisition.acquisition_id
    assert data["lens_correction"] is True


@pytest.mark.asyncio
async def test_get_current_lens_correction_not_found(async_client: AsyncClient):
    """Test 404 when no matching lens correction exists."""
    response = await async_client.get(
        "/api/v2/lens-corrections/current",
        params={
            "scope_id": "TEM_NONEXISTENT",
            "magnification": 9999,
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_latest_lens_correction(async_client: AsyncClient, lens_correction_acquisition):
    """Test getting latest lens correction for scope."""
    response = await async_client.get(
        "/api/v2/lens-corrections/latest",
        params={"scope_id": "TEM1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["acquisition_id"] == lens_correction_acquisition.acquisition_id


@pytest.mark.asyncio
async def test_list_lens_corrections(async_client: AsyncClient, lens_correction_acquisition):
    """Test listing lens corrections with filters."""
    response = await async_client.get(
        "/api/v2/lens-corrections",
        params={"scope_id": "TEM1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "lens_corrections" in data
    assert len(data["lens_corrections"]) >= 1


@pytest.mark.asyncio
async def test_get_acquisition_lens_correction(
    async_client: AsyncClient, acquisition_with_lc, lens_correction_acquisition
):
    """Test getting the lens correction used by an acquisition."""
    response = await async_client.get(f"/api/v2/acquisitions/{acquisition_with_lc.acquisition_id}/lens-correction")
    assert response.status_code == 200
    data = response.json()
    assert data["acquisition_id"] == lens_correction_acquisition.acquisition_id


@pytest.mark.asyncio
async def test_get_acquisitions_by_lens_correction(
    async_client: AsyncClient, acquisition_with_lc, lens_correction_acquisition
):
    """Test getting all acquisitions that used a lens correction."""
    response = await async_client.get(
        f"/api/v2/lens-corrections/{lens_correction_acquisition.acquisition_id}/acquisitions"
    )
    assert response.status_code == 200
    data = response.json()
    assert "acquisitions" in data
    assert any(a["acquisition_id"] == acquisition_with_lc.acquisition_id for a in data["acquisitions"])


@pytest.mark.asyncio
async def test_find_orphan_acquisitions(async_client: AsyncClient, test_acquisition):
    """Test finding acquisitions without lens correction reference."""
    response = await async_client.get("/api/v2/lens-corrections/orphans")
    assert response.status_code == 200
    data = response.json()
    assert "acquisitions" in data
    assert any(a["acquisition_id"] == test_acquisition.acquisition_id for a in data["acquisitions"])


@pytest.mark.asyncio
async def test_create_acquisition_with_invalid_lens_correction_reference(
    async_client: AsyncClient, test_roi, test_acquisition_task
):
    """Test that creating an acquisition with non-existent LC reference fails."""
    response = await async_client.post(
        "/api/v2/acquisitions",
        json={
            "acquisition_id": "ACQ_INVALID_LC",
            "montage_id": "MONTAGE_INVALID_LC",
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "hardware_settings": {
                "scope_id": "TEM1",
                "camera_model": "Test",
                "camera_serial": "123",
                "camera_bit_depth": 16,
                "media_type": "tape",
            },
            "acquisition_settings": {
                "magnification": 2000,
                "spot_size": 3,
                "exposure_time": 100,
                "tile_size": [4096, 4096],
                "tile_overlap": 0.1,
                "saved_bit_depth": 8,
            },
            "tilt_angle": 0.0,
            "lens_correction": False,
            "lens_correction_acquisition_id": "NONEXISTENT_LC",
        },
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_acquisition_referencing_non_lc_acquisition(
    async_client: AsyncClient, test_acquisition, test_roi, test_acquisition_task
):
    """Test that referencing a non-LC acquisition as LC fails."""
    response = await async_client.post(
        "/api/v2/acquisitions",
        json={
            "acquisition_id": "ACQ_BAD_REF",
            "montage_id": "MONTAGE_BAD_REF",
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "hardware_settings": {
                "scope_id": "TEM1",
                "camera_model": "Test",
                "camera_serial": "123",
                "camera_bit_depth": 16,
                "media_type": "tape",
            },
            "acquisition_settings": {
                "magnification": 2000,
                "spot_size": 3,
                "exposure_time": 100,
                "tile_size": [4096, 4096],
                "tile_overlap": 0.1,
                "saved_bit_depth": 8,
            },
            "tilt_angle": 0.0,
            "lens_correction": False,
            "lens_correction_acquisition_id": test_acquisition.acquisition_id,  # Not a LC!
        },
    )
    assert response.status_code == 400
    assert "not a lens correction" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_lens_correction_with_lc_reference_fails(
    async_client: AsyncClient, lens_correction_acquisition, test_roi, test_acquisition_task
):
    """Test that LC acquisitions cannot reference another LC."""
    response = await async_client.post(
        "/api/v2/acquisitions",
        json={
            "acquisition_id": "LC_WITH_REF",
            "montage_id": "LC_MONTAGE_WITH_REF",
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "hardware_settings": {
                "scope_id": "TEM1",
                "camera_model": "Test",
                "camera_serial": "123",
                "camera_bit_depth": 16,
                "media_type": "tape",
            },
            "acquisition_settings": {
                "magnification": 2000,
                "spot_size": 3,
                "exposure_time": 100,
                "tile_size": [4096, 4096],
                "tile_overlap": 0.5,
                "saved_bit_depth": 8,
            },
            "tilt_angle": 0.0,
            "lens_correction": True,
            "lens_correction_acquisition_id": lens_correction_acquisition.acquisition_id,
        },
    )
    assert response.status_code == 400
    assert "cannot reference" in response.json()["detail"].lower()
