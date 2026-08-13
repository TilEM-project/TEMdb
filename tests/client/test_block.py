from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.block import BlockResource
from temdb.models import BlockCreate, BlockUpdate

API = "http://test/api/v2"


def _resource():
    request = AsyncMock()
    return BlockResource(request, API), request


def _block_payload(**extra) -> dict:
    return {
        "id": 1,
        "block_id": "BLOCK001",
        "specimen_id": "SPEC001",
        **extra,
    }


@pytest.mark.asyncio
async def test_create_posts_block():
    res, request = _resource()
    request.return_value = _block_payload()
    out = await res.create(BlockCreate(block_id="BLOCK001", specimen_id="SPEC001"))
    assert request.await_args.args[:2] == ("POST", "blocks")
    assert request.await_args.kwargs["json"] == {"block_id": "BLOCK001", "specimen_id": "SPEC001"}
    assert out.block_id == "BLOCK001"


@pytest.mark.asyncio
async def test_create_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _block_payload(block_id="BLOCK002")
    out = await res.create(block_id="BLOCK002", specimen_id="SPEC001")
    assert request.await_args.kwargs["json"] == {"block_id": "BLOCK002", "specimen_id": "SPEC001"}
    assert out.block_id == "BLOCK002"


@pytest.mark.asyncio
async def test_create_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.create(BlockCreate(block_id="BLOCK001", specimen_id="SPEC001"), description="conflict")


@pytest.mark.asyncio
async def test_list_by_specimen_uses_scoped_path():
    res, request = _resource()
    request.return_value = [_block_payload(), _block_payload(block_id="BLOCK002")]
    out = await res.list_by_specimen("SPEC001", skip=3, limit=2)
    assert request.await_args.args[:2] == ("GET", "blocks/specimens/SPEC001/blocks")
    assert request.await_args.kwargs["params"] == {"skip": 3, "limit": 2}
    assert [b.block_id for b in out] == ["BLOCK001", "BLOCK002"]


@pytest.mark.asyncio
async def test_get_uses_scoped_path():
    res, request = _resource()
    request.return_value = _block_payload()
    out = await res.get("SPEC001", "BLOCK001")
    assert request.await_args.args[:2] == ("GET", "blocks/specimens/SPEC001/blocks/BLOCK001")
    assert out.specimen_id == "SPEC001"


@pytest.mark.asyncio
async def test_update_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _block_payload(description="updated")
    out = await res.update("SPEC001", "BLOCK001", description="updated")
    assert request.await_args.args[:2] == ("PATCH", "blocks/specimens/SPEC001/blocks/BLOCK001")
    assert request.await_args.kwargs["json"] == {"description": "updated"}
    assert out.description == "updated"


@pytest.mark.asyncio
async def test_update_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.update("SPEC001", "BLOCK001", BlockUpdate(description="d"), microCT_info={})


@pytest.mark.asyncio
async def test_delete_uses_delete_method():
    res, request = _resource()
    request.return_value = None
    await res.delete("SPEC001", "BLOCK001")
    assert request.await_args.args[:2] == ("DELETE", "blocks/specimens/SPEC001/blocks/BLOCK001")
