from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.section import SectionResource
from temdb.models import SectionCreate, SectionUpdate

API = "http://test/api/v2"
NOW = datetime(2026, 8, 4, tzinfo=timezone.utc)


def _resource():
    request = AsyncMock()
    return SectionResource(request, API), request


def _section_payload(**extra) -> dict:
    return {
        "id": 1,
        "section_id": "MEDIA001_S00001",
        "cutting_session_id": "CUT001",
        "block_id": "BLK001",
        "specimen_id": "SPEC001",
        "media_id": "MEDIA001",
        "section_number": 1,
        "timestamp": NOW.isoformat(),
        "condition": "ok",
        **extra,
    }


@pytest.mark.asyncio
async def test_create_posts_section():
    res, request = _resource()
    request.return_value = _section_payload()
    out = await res.create(SectionCreate(cutting_session_id="CUT001", section_number=1, media_id="MEDIA001"))
    assert request.await_args.args[:2] == ("POST", "sections")
    assert request.await_args.kwargs["json"]["cutting_session_id"] == "CUT001"
    assert out.section_id == "MEDIA001_S00001"


@pytest.mark.asyncio
async def test_create_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _section_payload(section_id="MEDIA001_S00002", section_number=2)
    out = await res.create(cutting_session_id="CUT001", section_number=2, media_id="MEDIA001")
    assert request.await_args.kwargs["json"]["section_number"] == 2
    assert out.section_number == 2


@pytest.mark.asyncio
async def test_create_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.create(
            SectionCreate(cutting_session_id="CUT001", section_number=1, media_id="MEDIA001"),
            barcode="conflict",
        )


@pytest.mark.asyncio
async def test_list_by_session_uses_expected_path():
    res, request = _resource()
    request.return_value = [_section_payload(), _section_payload(section_id="MEDIA001_S00002", section_number=2)]
    out = await res.list_by_session("CUT001", limit=2)
    assert request.await_args.args[:2] == ("GET", "sections/sessions/CUT001")
    assert request.await_args.kwargs["params"] == {"skip": 0, "limit": 2}
    assert [s.section_number for s in out] == [1, 2]


@pytest.mark.asyncio
async def test_update_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _section_payload(condition="damaged")
    out = await res.update("CUT001", "MEDIA001_S00001", condition="damaged")
    assert request.await_args.args[:2] == ("PATCH", "sections/sessions/CUT001/sections/MEDIA001_S00001")
    assert request.await_args.kwargs["json"] == {"condition": "damaged"}
    assert out.condition == "damaged"


@pytest.mark.asyncio
async def test_update_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(AssertionError):
        await res.update("CUT001", "MEDIA001_S00001", SectionUpdate(condition="ok"), condition_reason="conflict")
