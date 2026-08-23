from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.acquisition import AcquisitionResource
from temdb.client.resources.roi import ROIResource

API = "http://test/api/v2"


def _tile(raster_index: int) -> dict:
    return {
        "tile_id": f"018f-{raster_index}",
        "acquisition_id": "ACQ1",
        "raster_index": raster_index,
        "stage_position": {"x": 0.0, "y": 0.0},
        "raster_position": {"row": 0, "col": raster_index},
        "focus_score": 0.9,
        "min_value": 0,
        "max_value": 255,
        "mean_value": 128,
        "std_value": 25,
        "image_path": "/p.tif",
    }


@pytest.mark.asyncio
async def test_get_all_tiles_follows_pagination():
    request = AsyncMock()
    res = AcquisitionResource(request, API)
    request.side_effect = [
        {"tiles": [_tile(0), _tile(1)], "metadata": {"has_more": True, "next_cursor": 1}},
        {"tiles": [_tile(2)], "metadata": {"has_more": False, "next_cursor": None}},
    ]
    tiles = await res.get_all_tiles("ACQ1", page_limit=2)
    assert [t.raster_index for t in tiles] == [0, 1, 2]
    assert request.await_count == 2


@pytest.mark.asyncio
async def test_get_all_tiles_single_page():
    request = AsyncMock()
    res = AcquisitionResource(request, API)
    request.return_value = {"tiles": [_tile(0)], "metadata": {"has_more": False, "next_cursor": None}}
    tiles = await res.get_all_tiles("ACQ1")
    assert len(tiles) == 1
    assert request.await_count == 1


@pytest.mark.asyncio
async def test_roi_list_acquisitions_filters_by_roi_and_status():
    request = AsyncMock()
    res = ROIResource(request, API)
    request.return_value = {
        "acquisitions": [
            {
                "id": 1,
                "acquisition_id": "ACQ1",
                "montage_id": "M",
                "specimen_id": "S",
                "roi_id": "R",
                "acquisition_task_id": "T",
                "run_id": "0190a6b2-7c3e-7000-8000-000000000001",
                "microscope_id": "0190a6b2-7c3e-7000-8000-000000000002",
                "kind": "montage",
                "hardware_settings": {
                    "camera_model": "FalconIV",
                    "camera_serial": "SN001",
                    "camera_bit_depth": 16,
                    "media_type": "carbon-film",
                },
                "acquisition_settings": {
                    "magnification": 10000,
                    "spot_size": 3,
                    "exposure_time": 100,
                    "tile_size": [4096, 4096],
                    "tile_overlap": 0.1,
                    "saved_bit_depth": 8,
                },
                # old qc-passed maps to status=complete + qc_state=qc_pass
                "status": "complete",
                "qc_state": "qc_pass",
                "transfer_state": "not_started",
                "start_time": "2026-06-09T00:00:00Z",
                "end_time": "2026-06-09T01:00:00Z",
            }
        ],
        "metadata": {},
    }
    out = await res.list_acquisitions("R", status="complete")
    assert request.await_args.args[1] == "acquisitions"
    assert request.await_args.kwargs["params"]["roi_id"] == "R"
    assert request.await_args.kwargs["params"]["status"] == "complete"
    assert out[0].acquisition_id == "ACQ1"
    assert out[0].qc_state == "qc_pass"


@pytest.mark.asyncio
async def test_roi_list_acquisitions_passes_qc_state():
    request = AsyncMock()
    res = ROIResource(request, API)
    request.return_value = {"acquisitions": [], "metadata": {}}
    out = await res.list_acquisitions("R", status="in_flight", qc_state="needs_review")
    params = request.await_args.kwargs["params"]
    assert params["status"] == "in_flight"
    assert params["qc_state"] == "needs_review"
    assert out == []


@pytest.mark.asyncio
async def test_acquisition_list_passes_status_and_qc_state():
    request = AsyncMock()
    res = AcquisitionResource(request, API)
    request.return_value = {"acquisitions": [], "metadata": {}}
    await res.list(status="in_flight", qc_state="pending")
    assert request.await_args.args[1] == "acquisitions"
    params = request.await_args.kwargs["params"]
    assert params["status"] == "in_flight"
    assert params["qc_state"] == "pending"


@pytest.mark.asyncio
async def test_acquisition_list_with_full_metadata_passes_status():
    request = AsyncMock()
    res = AcquisitionResource(request, API)
    request.return_value = {"acquisitions": [], "metadata": {}}
    await res.list_with_full_metadata(status="failed")
    params = request.await_args.kwargs["params"]
    assert params["status"] == "failed"
