from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from temdb.client.resources.acquisition import AcquisitionResource
from temdb.models import AcquisitionCreate, AcquisitionUpdate

API = "http://test/api/v2"
NOW = datetime(2026, 8, 4, tzinfo=timezone.utc)
MICROSCOPE_ID = str(uuid4())


def _resource():
    request = AsyncMock()
    return AcquisitionResource(request, API), request


def _hardware_settings() -> dict:
    return {
        "scope_id": "scope-1",
        "camera_model": "cam-x",
        "camera_serial": "123",
        "camera_bit_depth": 16,
        "media_type": "wafer",
    }


def _acquisition_settings() -> dict:
    return {
        "magnification": 20000,
        "spot_size": 2,
        "exposure_time": 150,
        "tile_size": [4096, 4096],
        "tile_overlap": 0.1,
        "saved_bit_depth": 8,
    }


def _acquisition_payload(**extra) -> dict:
    return {
        "id": 1,
        "acquisition_id": "ACQ001",
        "run_id": str(uuid4()),
        "montage_id": "MONT001",
        "specimen_id": "SPEC001",
        "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001",
        "acquisition_task_id": "TASK001",
        "microscope_id": MICROSCOPE_ID,
        "dataset_id": None,
        "kind": "montage",
        "lc_id": None,
        "hardware_settings": _hardware_settings(),
        "acquisition_settings": _acquisition_settings(),
        "qc_state": "pending",
        "transfer_state": "not_started",
        "start_time": NOW.isoformat(),
        **extra,
    }


def _tile_payload(**extra) -> dict:
    return {
        "tile_id": str(uuid4()),
        "acquisition_id": "ACQ001",
        "raster_index": 0,
        "stage_position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "raster_position": {"row": 0, "col": 0},
        "focus_score": 0.95,
        "min_value": 5.0,
        "max_value": 255.0,
        "mean_value": 120.0,
        "std_value": 15.0,
        "image_path": "s3://bucket/tile-0.tiff",
        **extra,
    }


@pytest.mark.asyncio
async def test_list_returns_paginated_model():
    res, request = _resource()
    request.return_value = {"acquisitions": [_acquisition_payload()], "metadata": {"has_more": False}}
    out = await res.list(limit=1)
    assert request.await_args.args[:2] == ("GET", "acquisitions")
    assert out.acquisitions[0].acquisition_id == "ACQ001"


@pytest.mark.asyncio
async def test_create_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _acquisition_payload(acquisition_id="ACQ002")
    out = await res.create(
        acquisition_id="ACQ002",
        montage_id="MONT002",
        acquisition_task_id="TASK002",
        microscope_id=MICROSCOPE_ID,
        hardware_settings=_hardware_settings(),
        acquisition_settings=_acquisition_settings(),
    )
    assert request.await_args.args[:2] == ("POST", "acquisitions")
    assert request.await_args.kwargs["json"]["acquisition_id"] == "ACQ002"
    assert out.acquisition_id == "ACQ002"


@pytest.mark.asyncio
async def test_create_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.create(
            AcquisitionCreate(
                acquisition_id="ACQ001",
                montage_id="MONT001",
                acquisition_task_id="TASK001",
                microscope_id=MICROSCOPE_ID,
                hardware_settings=_hardware_settings(),
                acquisition_settings=_acquisition_settings(),
            ),
            montage_set_name="conflict",
        )


@pytest.mark.asyncio
async def test_update_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _acquisition_payload(status="complete", qc_state="qc_pass", transfer_state="complete")
    out = await res.update("ACQ001", status="complete", qc_state="qc_pass", transfer_state="complete")
    assert request.await_args.args[:2] == ("PATCH", "acquisitions/ACQ001")
    assert request.await_args.kwargs["json"] == {
        "status": "complete",
        "qc_state": "qc_pass",
        "transfer_state": "complete",
    }
    assert out.status == "complete"


@pytest.mark.asyncio
async def test_update_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.update("ACQ001", AcquisitionUpdate(status="failed"), error_message="conflict")


@pytest.mark.asyncio
async def test_add_tile_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _tile_payload()
    out = await res.add_tile(
        "ACQ001",
        raster_index=0,
        stage_position={"x": 0.0, "y": 0.0, "z": 0.0},
        raster_position={"row": 0, "col": 0},
        focus_score=0.95,
        min_value=5.0,
        max_value=255.0,
        mean_value=120.0,
        std_value=15.0,
        image_path="s3://bucket/tile-0.tiff",
    )
    assert request.await_args.args[:2] == ("POST", "acquisitions/ACQ001/tiles")
    assert request.await_args.kwargs["json"]["raster_index"] == 0
    assert out.acquisition_id == "ACQ001"


@pytest.mark.asyncio
async def test_add_storage_location_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _acquisition_payload()
    out = await res.add_storage_location("ACQ001", location_type="s3", base_path="s3://bucket/acq", metadata={})
    assert request.await_args.args[:2] == ("POST", "acquisitions/ACQ001/storage-locations")
    assert request.await_args.kwargs["json"]["location_type"] == "s3"
    assert out.acquisition_id == "ACQ001"


@pytest.mark.asyncio
async def test_delete_uses_delete_method():
    res, request = _resource()
    request.return_value = None
    await res.delete("ACQ001")
    assert request.await_args.args[:2] == ("DELETE", "acquisitions/ACQ001")
