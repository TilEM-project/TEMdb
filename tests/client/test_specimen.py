from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.specimen import SpecimenResource
from temdb.models import SpecimenCreate, SpecimenUpdate

API = "http://test/api/v2"


def _resource():
    request = AsyncMock()
    return SpecimenResource(request, API), request


def _specimen_payload(**extra) -> dict:
    return {
        "id": 1,
        "specimen_id": "SPEC001",
        "description": "test specimen",
        "specimen_images": ["s3://bucket/specimen.png"],
        **extra,
    }


def _block_payload(**extra) -> dict:
    return {
        "id": 10,
        "block_id": "BLOCK001",
        "specimen_id": "SPEC001",
        **extra,
    }


@pytest.mark.asyncio
async def test_create_posts_specimen():
    res, request = _resource()
    request.return_value = _specimen_payload()
    out = await res.create(SpecimenCreate(specimen_id="SPEC001", description="test specimen"))
    assert request.await_args.args[:2] == ("POST", "specimens")
    assert request.await_args.kwargs["json"]["specimen_id"] == "SPEC001"
    assert out.specimen_id == "SPEC001"


@pytest.mark.asyncio
async def test_create_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _specimen_payload(specimen_id="SPEC002", description="created from kwargs")
    out = await res.create(specimen_id="SPEC002", description="created from kwargs")
    assert request.await_args.kwargs["json"] == {"specimen_id": "SPEC002", "description": "created from kwargs"}
    assert out.specimen_id == "SPEC002"
    assert out.description == "created from kwargs"


@pytest.mark.asyncio
async def test_create_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.create(SpecimenCreate(specimen_id="SPEC001"), description="conflict")


@pytest.mark.asyncio
async def test_get_uses_specimen_path():
    res, request = _resource()
    request.return_value = _specimen_payload()
    out = await res.get("SPEC001")
    assert request.await_args.args[:2] == ("GET", "specimens/SPEC001")
    assert out.specimen_id == "SPEC001"


@pytest.mark.asyncio
async def test_list_returns_models():
    res, request = _resource()
    request.return_value = [_specimen_payload(), _specimen_payload(specimen_id="SPEC002")]
    out = await res.list(limit=2)
    assert request.await_args.args[:2] == ("GET", "specimens")
    assert request.await_args.kwargs["params"] == {"skip": 0, "limit": 2}
    assert [specimen.specimen_id for specimen in out] == ["SPEC001", "SPEC002"]


@pytest.mark.asyncio
async def test_update_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _specimen_payload(description="updated")
    out = await res.update("SPEC001", description="updated")
    assert request.await_args.args[:2] == ("PATCH", "specimens/SPEC001")
    assert request.await_args.kwargs["json"] == {"description": "updated"}
    assert out.description == "updated"


@pytest.mark.asyncio
async def test_update_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.update("SPEC001", SpecimenUpdate(description="a"), functional_imaging_metadata={})


@pytest.mark.asyncio
async def test_delete_uses_delete_method():
    res, request = _resource()
    request.return_value = None
    await res.delete("SPEC001")
    assert request.await_args.args[:2] == ("DELETE", "specimens/SPEC001")


@pytest.mark.asyncio
async def test_add_image_posts_payload():
    res, request = _resource()
    request.return_value = _specimen_payload(specimen_images=["s3://bucket/specimen.png", "s3://bucket/new.png"])
    out = await res.add_image("SPEC001", "s3://bucket/new.png")
    assert request.await_args.args[:2] == ("POST", "specimens/SPEC001/images")
    assert request.await_args.kwargs["json"] == {"image_url": "s3://bucket/new.png"}
    assert "s3://bucket/new.png" in out.specimen_images


@pytest.mark.asyncio
async def test_remove_image_uses_delete_with_query():
    res, request = _resource()
    request.return_value = _specimen_payload(specimen_images=["s3://bucket/specimen.png"])
    out = await res.remove_image("SPEC001", "s3://bucket/remove.png")
    assert request.await_args.args[:2] == ("DELETE", "specimens/SPEC001/images")
    assert request.await_args.kwargs["params"] == {"image_url": "s3://bucket/remove.png"}
    assert out.specimen_id == "SPEC001"


@pytest.mark.asyncio
async def test_list_blocks_returns_models():
    res, request = _resource()
    request.return_value = [_block_payload(), _block_payload(block_id="BLOCK002")]
    out = await res.list_blocks("SPEC001", skip=5, limit=10)
    assert request.await_args.args[:2] == ("GET", "specimens/SPEC001/blocks")
    assert request.await_args.kwargs["params"] == {"skip": 5, "limit": 10}
    assert [block.block_id for block in out] == ["BLOCK001", "BLOCK002"]
