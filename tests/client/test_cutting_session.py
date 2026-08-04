from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.cutting_session import CuttingSessionResource
from temdb.models import CuttingSessionCreate, CuttingSessionUpdate

API = "http://test/api/v2"
NOW = datetime(2026, 8, 1, tzinfo=timezone.utc)


def _resource():
    request = AsyncMock()
    return CuttingSessionResource(request, API), request


def _session_payload(**extra) -> dict:
    return {
        "id": 1,
        "cutting_session_id": "CUT001",
        "specimen_id": "SPEC001",
        "block_id": "BLOCK001",
        "start_time": NOW.isoformat(),
        "sectioning_device": "Leica",
        "media_type": "wafer",
        **extra,
    }


@pytest.mark.asyncio
async def test_create_posts_session():
    res, request = _resource()
    request.return_value = _session_payload()
    out = await res.create(
        CuttingSessionCreate(
            cutting_session_id="CUT001",
            block_id="BLOCK001",
            start_time=NOW,
            sectioning_device="Leica",
            media_type="wafer",
        )
    )
    assert request.await_args.args[:2] == ("POST", "cutting-sessions")
    assert request.await_args.kwargs["json"]["cutting_session_id"] == "CUT001"
    assert out.cutting_session_id == "CUT001"


@pytest.mark.asyncio
async def test_create_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _session_payload(cutting_session_id="CUT002")
    out = await res.create(
        cutting_session_id="CUT002",
        block_id="BLOCK001",
        start_time=NOW,
        sectioning_device="Leica",
        media_type="wafer",
    )
    assert request.await_args.kwargs["json"]["cutting_session_id"] == "CUT002"
    assert out.cutting_session_id == "CUT002"


@pytest.mark.asyncio
async def test_create_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.create(
            CuttingSessionCreate(
                cutting_session_id="CUT001",
                block_id="BLOCK001",
                start_time=NOW,
                sectioning_device="Leica",
                media_type="wafer",
            ),
            operator="conflict",
        )


@pytest.mark.asyncio
async def test_list_by_block_uses_nested_path():
    res, request = _resource()
    request.return_value = [_session_payload(), _session_payload(cutting_session_id="CUT002")]
    out = await res.list_by_block("SPEC001", "BLOCK001", limit=2)
    assert request.await_args.args[:2] == ("GET", "cutting-sessions/specimens/SPEC001/blocks/BLOCK001/sessions")
    assert request.await_args.kwargs["params"] == {"skip": 0, "limit": 2}
    assert [s.cutting_session_id for s in out] == ["CUT001", "CUT002"]


@pytest.mark.asyncio
async def test_update_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _session_payload(operator="cam")
    out = await res.update("CUT001", operator="cam")
    assert request.await_args.args[:2] == ("PATCH", "cutting-sessions/CUT001")
    assert request.await_args.kwargs["json"] == {"operator": "cam"}
    assert out.operator == "cam"


@pytest.mark.asyncio
async def test_update_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.update("CUT001", CuttingSessionUpdate(operator="cam"), end_time=NOW)


@pytest.mark.asyncio
async def test_delete_uses_delete_method():
    res, request = _resource()
    request.return_value = None
    await res.delete("CUT001")
    assert request.await_args.args[:2] == ("DELETE", "cutting-sessions/CUT001")
