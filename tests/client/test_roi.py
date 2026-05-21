import httpx

from temdb.models import ROICreate, ROIUpdate


def _roi_resp(roi_id: str = "ROI001") -> dict:
    return {
        "roi_id": roi_id,
        "roi_number": 1,
        "section_id": "SEC001",
        "specimen_id": "SPEC001",
        "block_id": "B1",
        "substrate_media_id": "M1",
        "hierarchy_level": 1,
    }


async def test_create_posts_required_fields(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_roi_resp()))
    await client.roi.create(
        ROICreate(
            section_id="SEC001",
            specimen_id="SPEC001",
            block_id="B1",
            substrate_media_id="M1",
            roi_number=1,
        )
    )
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/rois"
    assert req.body == {
        "section_id": "SEC001",
        "specimen_id": "SPEC001",
        "block_id": "B1",
        "substrate_media_id": "M1",
        "roi_number": 1,
    }


async def test_list_by_section(client, captured):
    await client.roi.list_by_section("SEC001", skip=0, limit=10)
    req = captured[-1]
    assert req.path == "/api/v2/sections/SEC001/rois"


async def test_list_all_with_is_parent(client, captured):
    await client.roi.list_all(specimen_id="SPEC001", is_parent_roi=True)
    req = captured[-1]
    assert req.path == "/api/v2/rois"
    assert req.params["is_parent_roi"] in ("True", "true")
    assert req.params["specimen_id"] == "SPEC001"


async def test_get(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_roi_resp("42")))
    await client.roi.get(42)
    assert captured[-1].path == "/api/v2/rois/42"


async def test_update_patches(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_roi_resp("42")))
    await client.roi.update(42, ROIUpdate(roi_number=2))
    req = captured[-1]
    assert req.method == "PATCH"
    assert req.path == "/api/v2/rois/42"
    assert req.body == {"roi_number": 2}


async def test_delete(client, captured):
    await client.roi.delete(42)
    req = captured[-1]
    assert req.method == "DELETE"
    assert req.path == "/api/v2/rois/42"


async def test_get_children(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={"children": [], "metadata": {}}))
    await client.roi.get_children(42, skip=0, limit=10)
    req = captured[-1]
    assert req.path == "/api/v2/rois/42/children"
    assert req.params == {"skip": "0", "limit": "10"}
