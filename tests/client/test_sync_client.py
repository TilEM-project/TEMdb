from datetime import datetime

import httpx

from temdb.models import (
    AcquisitionCreate,
    AcquisitionTaskCreate,
    BlockCreate,
    CuttingSessionCreate,
    ROICreate,
    SectionCreate,
    SpecimenCreate,
    SubstrateCreate,
)
from temdb.models.acquisition import (
    AcquisitionParams,
    AcquisitionStatus,
    HardwareParams,
)
from temdb.models.substrate import SubstrateMetadata


def test_sync_substrate_create_serializes_datetime(sync_client, captured, response_queue):
    """Same datetime regression as the async test — proves sync path serializes too."""
    response_queue.append(httpx.Response(200, json={"media_id": "M1", "media_type": "GridDisc"}))
    meta = SubstrateMetadata(
        name="wafer1",
        created=datetime(2026, 1, 2, 3, 4, 5),
        calibrated=datetime(2026, 1, 2, 3, 4, 6),
    )
    sync_client.substrate.create(SubstrateCreate(media_id="M1", media_type="GridDisc", metadata=meta))
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/substrates"
    assert req.body["metadata"]["created"] == "2026-01-02T03:04:05"


def test_sync_specimen_create(sync_client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={"specimen_id": "SPEC001"}))
    sync_client.specimen.create(SpecimenCreate(specimen_id="SPEC001"))
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/specimens"
    assert req.body == {"specimen_id": "SPEC001"}


def test_sync_block_create(sync_client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={"specimen_id": "SPEC001", "block_id": "B1"}))
    sync_client.block.create(BlockCreate(specimen_id="SPEC001", block_id="B1"))
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/blocks"
    assert req.body == {"specimen_id": "SPEC001", "block_id": "B1"}


def test_sync_cutting_session_create(sync_client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={
        "cutting_session_id": "CUT001", "specimen_id": "SPEC001", "block_id": "B1",
        "start_time": "2026-01-02T03:04:05", "sectioning_device": "dev", "media_type": "tape",
    }))
    sync_client.cutting_session.create(CuttingSessionCreate(
        cutting_session_id="CUT001", block_id="B1",
        start_time=datetime(2026, 1, 2, 3, 4, 5),
        sectioning_device="dev", media_type="tape",
    ))
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/cutting-sessions"
    assert req.body["start_time"] == "2026-01-02T03:04:05"


def test_sync_section_create(sync_client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={
        "section_id": "SEC001", "section_number": 1, "cutting_session_id": "CUT001",
        "block_id": "B1", "specimen_id": "SPEC001", "media_id": "M1",
    }))
    sync_client.section.create(SectionCreate(
        cutting_session_id="CUT001", section_number=1, media_id="M1",
    ))
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/sections"


def test_sync_roi_create(sync_client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={
        "roi_id": "ROI001", "roi_number": 1, "section_id": "SEC001",
        "specimen_id": "SPEC001", "block_id": "B1", "substrate_media_id": "M1",
        "hierarchy_level": 1,
    }))
    sync_client.roi.create(ROICreate(
        section_id="SEC001", specimen_id="SPEC001", block_id="B1",
        substrate_media_id="M1", roi_number=1,
    ))
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/rois"
    assert req.body["roi_number"] == 1


def test_sync_task_create(sync_client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={
        "task_id": "TASK001", "specimen_id": "SPEC001", "block_id": "B1",
        "roi_id": "ROI001", "task_type": "standard_acquisition",
        "version": 1, "status": "Planned",
    }))
    sync_client.acquisition_task.create(AcquisitionTaskCreate(
        task_id="TASK001", specimen_id="SPEC001", block_id="B1",
        roi_id="ROI001", task_type="standard_acquisition",
    ))
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/acquisition-tasks"
    assert req.body["task_id"] == "TASK001"


def test_sync_acquisition_create(sync_client, captured, response_queue):
    hw = {"scope_id": "S1", "camera_model": "cm", "camera_serial": "cs",
          "camera_bit_depth": 16, "media_type": "tape"}
    ap = {"magnification": 1000, "spot_size": 3, "exposure_time": 100,
          "tile_size": [4096, 4096], "tile_overlap": 0.1, "saved_bit_depth": 8}
    response_queue.append(httpx.Response(200, json={
        "acquisition_id": "ACQ001", "montage_id": "M001", "specimen_id": "SPEC001",
        "roi_id": "ROI001", "acquisition_task_id": "TASK001",
        "hardware_settings": hw, "acquisition_settings": ap,
        "status": AcquisitionStatus.IMAGING.value, "start_time": "2026-01-01T00:00:00",
    }))
    sync_client.acquisition.create(AcquisitionCreate(
        acquisition_id="ACQ001", montage_id="M001", roi_id="ROI001",
        acquisition_task_id="TASK001",
        hardware_settings=HardwareParams(**hw),
        acquisition_settings=AcquisitionParams(**ap),
        tilt_angle=0.0, lens_correction=False,
    ))
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/acquisitions"
    assert req.body["acquisition_id"] == "ACQ001"
