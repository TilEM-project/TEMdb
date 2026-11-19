import inspect
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from temdb.client import Page, TEMdbClient, TEMdbClientError
from temdb.client.resources.acquisition import AcquisitionResource
from temdb.client.resources.base import BaseResource
from temdb.client.resources.roi import ROIResource
from temdb.client.resources.section import SectionResource

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


def body(items: list, next_cursor: str | None, total: int = 0) -> dict:
    return {"items": items, "next_cursor": next_cursor, "total": total}


@pytest.fixture
def section_resource():
    request = AsyncMock()
    return SectionResource(request, "http://test/api/v2"), request


def sent(request) -> list[dict]:
    return [call.kwargs["params"] for call in request.await_args_list]


async def test_list_follows_next_cursor(section_resource):
    """Without paging arguments a list method follows next_cursor and returns every row."""
    resource, request = section_resource
    request.side_effect = [body(rows(0, 2), "c1"), body(rows(2, 4), "c2"), body(rows(4, 5), None)]

    result = await resource.list_by_media("MEDIA001")

    assert [section.id for section in result] == list(range(5))
    assert [params.get("cursor") for params in sent(request)] == [None, "c1", "c2"]
    assert all(params["limit"] == PAGE for params in sent(request))


async def test_one_page_returns_page(section_resource):
    """A limit returns that one page with its next_cursor and total."""
    resource, request = section_resource
    request.return_value = body(rows(0, 2), "tok", total=9)

    result = await resource.list_by_media("MEDIA001", limit=2)

    assert isinstance(result, Page)
    assert (len(result.items), result.next_cursor, result.total) == (2, "tok", 9)
    assert request.await_args.kwargs["params"] == {"limit": 2}


async def test_page_iterates_its_items(section_resource):
    """A page loops and measures like the list of its records."""
    resource, request = section_resource
    request.return_value = body(rows(0, 2), "tok", total=9)

    page = await resource.list_by_media("MEDIA001", limit=2)

    assert [section.id for section in page] == [0, 1]
    assert len(page) == 2
    assert page.items == list(page)


async def test_offset_is_sent(section_resource):
    """An offset alone returns one page fetched at that offset."""
    resource, request = section_resource
    request.return_value = body(rows(40, 42), None, total=42)

    result = await resource.list_by_media("MEDIA001", offset=40)

    assert result.items[0].id == 40
    assert request.await_args.kwargs["params"] == {"offset": 40, "limit": PAGE}


async def test_repeated_cursor_raises(section_resource):
    """A server that hands back the cursor it was sent raises instead of looping."""
    resource, request = section_resource
    request.side_effect = [body(rows(0, 1), "c1"), body(rows(0, 1), "c1")]

    with pytest.raises(TEMdbClientError, match="same page again"):
        await resource.list_by_media("MEDIA001")


async def test_too_many_pages_raises(section_resource):
    """A listing longer than max_pages raises."""
    resource, request = section_resource
    request.side_effect = lambda *args, params, **kwargs: body(rows(0, 1), f"c{params.get('cursor')}")

    with pytest.raises(TEMdbClientError, match="pages"):
        await resource._list("sections/media/MEDIA001", dict, {}, cursor=None, offset=None, limit=None, max_pages=3)


async def test_image_pages_follow_next_cursor():
    """The all-pages image helper follows next_cursor and joins the urls and errors."""
    request = AsyncMock(
        side_effect=[
            {"urls": {}, "errors": {"t1": "missing"}, "next_cursor": "c1"},
            {"urls": {}, "errors": {"t2": "missing"}, "next_cursor": None},
        ]
    )
    acquisitions = AcquisitionResource(request, "http://test/api/v2")

    result = await acquisitions.all_get_image_urls("A1", ["t1", "t2"])

    assert result.errors == {"t1": "missing", "t2": "missing"}
    assert [call.kwargs["params"].get("cursor") for call in request.await_args_list] == [None, "c1"]


@pytest.fixture
def client():
    return TEMdbClient("http://test")


async def test_iterate_streams_every_row(client, section_resource):
    """iterate yields each record and fetches the next page only when it is needed."""
    resource, request = section_resource
    request.side_effect = [body(rows(0, 2), "c1"), body(rows(2, 3), None)]

    records = client.iterate(resource.list_by_media, "MEDIA001", page_size=2)
    first = await anext(records)

    assert first.section_number == 1
    assert request.await_count == 1
    assert [section.section_number async for section in records] == [2, 3]
    assert [params.get("cursor") for params in sent(request)] == [None, "c1"]
    assert {params["limit"] for params in sent(request)} == {2}


async def test_iterate_passes_filters(client):
    """iterate sends the method's filters with every page."""
    request = AsyncMock(side_effect=[body([{"tile_id": "t1"}], "c2"), body([{"tile_id": "t2"}], None)])
    acquisitions = AcquisitionResource(request, "http://test/api/v2")

    tiles = [tile async for tile in client.iterate(acquisitions.get_tiles, "A1", page_size=1, fields=["tile_id"])]

    assert tiles == [{"tile_id": "t1"}, {"tile_id": "t2"}]
    assert all(params["limit"] == 1 and params["fields"] == ["tile_id"] for params in sent(request))


async def test_iterate_refuses_a_method_that_does_not_page(client):
    """iterate refuses a method without a cursor parameter."""
    rois = ROIResource(AsyncMock(), "http://test/api/v2")

    with pytest.raises(TypeError, match="get doesn't page"):
        await anext(client.iterate(rois.get, "R1"))


async def test_iterate_refuses_image_methods(client):
    """iterate refuses a method whose pages are not record listings."""
    request = AsyncMock(return_value={"urls": {}, "errors": {}, "next_cursor": None})
    acquisitions = AcquisitionResource(request, "http://test/api/v2")

    with pytest.raises(TypeError, match="get_image_urls doesn't page"):
        await anext(client.iterate(acquisitions.get_image_urls, "A1"))


@pytest.mark.parametrize("argument", ["cursor", "offset", "limit"])
async def test_iterate_refuses_its_own_arguments(client, section_resource, argument):
    """iterate refuses the paging arguments it sets itself."""
    resource, _ = section_resource

    with pytest.raises(TypeError, match=f"iterate sets {argument}"):
        await anext(client.iterate(resource.list_by_media, "MEDIA001", **{argument: 1}))
