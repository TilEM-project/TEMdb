from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.roi import ROIResource
from temdb.models import ROICreate, ROIUpdate

API = "http://test/api/v2"


def _resource():
    request = AsyncMock()
    return ROIResource(request, API), request


def _roi_payload(**extra) -> dict:
    return {
        "id": 1,
        "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001",
        "roi_number": 1,
        "section_id": "SEC001",
        "block_id": "BLK001",
        "specimen_id": "SPEC001",
        "substrate_media_id": "SUB001",
        "hierarchy_level": 1,
        "is_parent": False,
        "roi_payload": {"vertices": [[0, 0], [10, 10]]},
        **extra,
    }


@pytest.mark.asyncio
async def test_create_posts_roi():
    res, request = _resource()
    request.return_value = _roi_payload()
    out = await res.create(
        ROICreate(
            roi_number=1,
            section_id="SEC001",
            specimen_id="SPEC001",
            block_id="BLK001",
            substrate_media_id="SUB001",
        )
    )
    assert request.await_args.args[:2] == ("POST", "rois")
    assert request.await_args.kwargs["json"]["section_id"] == "SEC001"
    assert out.roi_id.endswith("ROI001")


@pytest.mark.asyncio
async def test_create_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _roi_payload(roi_id="SPEC001.BLK001.SEC001.SUB001.ROI002", roi_number=2)
    out = await res.create(
        roi_number=2,
        section_id="SEC001",
        specimen_id="SPEC001",
        block_id="BLK001",
        substrate_media_id="SUB001",
        payload={"vertices": [[1, 1], [20, 20]]},
    )
    assert request.await_args.kwargs["json"]["payload"] == {"vertices": [[1, 1], [20, 20]]}
    assert out.roi_number == 2


@pytest.mark.asyncio
async def test_create_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.create(
            ROICreate(
                roi_number=1,
                section_id="SEC001",
                specimen_id="SPEC001",
                block_id="BLK001",
                substrate_media_id="SUB001",
            ),
            payload={"vertices": [[0, 0], [1, 1]]},
        )


@pytest.mark.asyncio
async def test_list_by_section_uses_scoped_path():
    res, request = _resource()
    request.return_value = [_roi_payload(), _roi_payload(roi_number=2, roi_id="SPEC001.BLK001.SEC001.SUB001.ROI002")]
    out = await res.list_by_section("SEC001", limit=2)
    assert request.await_args.args[:2] == ("GET", "sections/SEC001/rois")
    assert request.await_args.kwargs["params"] == {"skip": 0, "limit": 2}
    assert [r.roi_number for r in out] == [1, 2]


@pytest.mark.asyncio
async def test_update_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _roi_payload(roi_payload={"vertices": [[3, 3], [30, 30]]})
    out = await res.update(1, payload={"vertices": [[3, 3], [30, 30]]})
    assert request.await_args.args[:2] == ("PATCH", "rois/1")
    assert request.await_args.kwargs["json"] == {"payload": {"vertices": [[3, 3], [30, 30]]}}
    assert out.roi_payload.vertices == [[3, 3], [30, 30]]


@pytest.mark.asyncio
async def test_update_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.update(1, ROIUpdate(payload={"vertices": [[1, 1], [2, 2]]}), payload={"vertices": []})


@pytest.mark.asyncio
async def test_delete_uses_delete_method():
    res, request = _resource()
    request.return_value = None
    await res.delete(1)
    assert request.await_args.args[:2] == ("DELETE", "rois/1")
