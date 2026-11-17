import inspect
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from temdb.client import Page, TEMdbClientError
from temdb.client.resources.base import BaseResource
from temdb.client.resources.section import SectionResource
from temdb.models import HAS_MORE_HEADER

PAGE = inspect.signature(BaseResource._list).parameters["page_size"].default
NOW = datetime(2026, 8, 4, tzinfo=timezone.utc)


def rows(start: int, stop: int) -> list[dict]:
    return [
        {
            "id": number,
            "section_id": f"MEDIA001_S{number:05d}",
            "cutting_session_id": "CUT001",
            "block_id": "BLK001",
            "specimen_id": "SPEC001",
            "media_id": "MEDIA001",
            "section_number": number + 1,
            "timestamp": NOW.isoformat(),
            "condition": "ok",
        }
        for number in range(start, stop)
    ]


def more(value: bool) -> dict:
    return {HAS_MORE_HEADER: "true" if value else "false"}


@pytest.fixture
def section_resource():
    request = AsyncMock()
    return SectionResource(request, "http://test/api/v2"), request


def skips(request) -> list[int]:
    return [call.kwargs["params"]["skip"] for call in request.await_args_list]


async def test_no_limit_follows_every_page(section_resource):
    resource, request = section_resource
    request.side_effect = [(rows(0, PAGE), more(True)), (rows(PAGE, PAGE + 1), more(False))]

    result = await resource.list_by_media("MEDIA001")

    assert [section.id for section in result] == list(range(PAGE + 1))
    assert skips(request) == [0, PAGE]
    assert all(call.kwargs["params"]["limit"] == PAGE for call in request.await_args_list)
    assert all(call.kwargs["with_headers"] is True for call in request.await_args_list)


async def test_limit_returns_one_page_with_has_more(section_resource):
    resource, request = section_resource
    request.return_value = (rows(0, 2), more(True))

    result = await resource.list_by_media("MEDIA001", limit=2)

    assert isinstance(result, Page) and result.has_more is True
    assert len(result) == 2
    assert request.await_args.kwargs["params"] == {"skip": 0, "limit": 2}


async def test_skip_alone_returns_one_page(section_resource):
    resource, request = section_resource
    request.return_value = (rows(5, 7), more(False))

    result = await resource.list_by_media("MEDIA001", skip=5)

    assert isinstance(result, Page) and result.has_more is False
    assert request.await_count == 1
    assert request.await_args.kwargs["params"] == {"skip": 5, "limit": PAGE}


async def test_exact_multiple_of_page_size_stops_on_header(section_resource):
    resource, request = section_resource
    request.side_effect = [(rows(0, PAGE), more(True)), (rows(PAGE, 2 * PAGE), more(False))]

    result = await resource.list_by_media("MEDIA001")

    assert len(result) == 2 * PAGE
    assert request.await_count == 2


async def test_server_ignoring_skip_raises(section_resource):
    resource, request = section_resource
    request.side_effect = [(rows(0, PAGE), more(True)), (rows(0, PAGE), more(True))]

    with pytest.raises(TEMdbClientError, match="ignored skip"):
        await resource.list_by_media("MEDIA001")


async def test_missing_header_falls_back_to_short_page(section_resource):
    resource, request = section_resource
    request.side_effect = [(rows(0, PAGE), {}), (rows(PAGE, PAGE + 3), {})]

    result = await resource.list_by_media("MEDIA001")

    assert len(result) == PAGE + 3
    assert request.await_count == 2


async def test_too_many_pages_raises(section_resource):
    resource, request = section_resource
    request.side_effect = lambda *args, params, **kwargs: (
        rows(params["skip"], params["skip"] + PAGE),
        more(True),
    )

    with pytest.raises(TEMdbClientError, match="pages"):
        await resource._list("sections/media/MEDIA001", dict, {}, skip=None, limit=None, max_pages=3)
