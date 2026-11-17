import inspect
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from functools import wraps
from itertools import takewhile
from typing import Any, TypeVar

from temdb.models import HAS_MORE_HEADER

from ..exceptions import TEMdbClientError

T = TypeVar("T")


class Page(list):
    def __init__(self, items=(), has_more: bool = False):
        super().__init__(items)
        self.has_more = has_more


class BaseResource:
    """Base class for API resources."""

    def __init__(self, request_func: Callable, base_url: str):
        self._request = request_func
        self._base_url = base_url
        self.logger = logging.getLogger(self.__class__.__name__)

    async def _get(self, endpoint: str, **kwargs) -> dict[str, Any]:
        return await self._request("GET", endpoint, **kwargs)

    async def _post(self, endpoint: str, data: dict[str, Any], **kwargs) -> dict[str, Any]:
        return await self._request("POST", endpoint, json=data, **kwargs)

    async def _patch(self, endpoint: str, data: dict[str, Any], **kwargs) -> dict[str, Any]:
        return await self._request("PATCH", endpoint, json=data, **kwargs)

    async def _delete(self, endpoint: str, **kwargs) -> None:
        return await self._request("DELETE", endpoint, **kwargs)

    async def _pages(
        self,
        fetch: Callable[[Any], Awaitable[Any]],
        next_position: Callable[[Any, Any], Any],
        start: Any = None,
        *,
        max_pages: int = 10_000,
    ) -> AsyncIterator[Any]:
        """Yield fetch(position) page by page; next_position(page, position) is where the next page starts, or None."""
        position = start
        for _ in range(max_pages):
            page = await fetch(position)
            yield page
            following = next_position(page, position)
            if following is None:
                return
            if following == position:
                raise TEMdbClientError("the server returned the same page again")
            position = following
        raise TEMdbClientError(f"more pages remain after {max_pages} pages")

    def _cursor_pages(self, fetch: Callable[[str | None], Awaitable[Any]]) -> AsyncIterator[Any]:
        return self._pages(fetch, _next_cursor)

    async def _list(
        self,
        endpoint: str,
        model: type[T],
        params: dict[str, Any],
        *,
        skip: int | None,
        limit: int | None,
        page_size: int = 100,
        max_pages: int = 10_000,
    ) -> list[T] | Page:
        if skip is not None or limit is not None:
            records, has_more = await self._page(endpoint, params, skip or 0, limit or page_size)
            return Page([model.model_validate(record) for record in records], has_more=has_more)
        everything: list[dict[str, Any]] = []
        previous_first = None
        pages = self._pages(
            lambda skip: self._page(endpoint, params, skip, page_size),
            lambda page, skip: skip + len(page[0]) if page[1] and page[0] else None,
            0,
            max_pages=max_pages,
        )
        async for records, _ in pages:
            if everything and records and records[0] == previous_first:
                raise TEMdbClientError(f"{endpoint}: the server ignored skip and returned the same page again")
            previous_first = records[0] if records else None
            everything += records
        return [model.model_validate(record) for record in everything]

    async def _page(
        self, endpoint: str, params: dict[str, Any], skip: int, limit: int
    ) -> tuple[list[dict[str, Any]], bool]:
        data, headers = await self._get(endpoint, params={**params, "skip": skip, "limit": limit}, with_headers=True)
        records = data if isinstance(data, list) else []
        flag = headers.get(HAS_MORE_HEADER)
        return records, (flag == "true") if flag is not None else len(records) == limit


def without_none(**values: Any) -> dict[str, Any]:
    """The keyword arguments whose value is not None, for building query parameters."""
    return {key: value for key, value in values.items() if value is not None}


def _next_cursor(page: Any, cursor: str | None) -> str | None:
    metadata = page["metadata"] if isinstance(page, dict) else page.metadata
    if isinstance(metadata, dict):
        return metadata.get("next_cursor") if metadata.get("has_more") else None
    return metadata.next_cursor if metadata.has_more else None


def accepts_keywords(model):
    """Let a create/update method take the model's fields as keywords instead of a built model."""

    def decorate(method):
        signature = inspect.signature(method)
        parameters = list(signature.parameters)[1:]

        @wraps(method)
        async def wrapper(self, *args, **kwargs):
            leading = list(takewhile(kwargs.__contains__, parameters[len(args) :]))
            args = (*args, *(kwargs.pop(name) for name in leading))
            named = [key for key, value in kwargs.items() if isinstance(value, model)]
            if named:
                args = (*args, kwargs.pop(named[0]))
            if not kwargs and signature.parameters[parameters[-1]].default is None:
                if len(args) == len(parameters) - 1 or (len(args) == len(parameters) and args[-1] is None):
                    return await method(self, *args)
            if args and isinstance(args[-1], model):
                if kwargs:
                    raise TypeError(f"Pass a {model.__name__} or its fields as keywords, not both")
                return await method(self, *args)
            return await method(self, *args, model(**kwargs))

        wrapper.__doc__ = f"{method.__doc__ or ''}\n\nTakes a {model.__name__} or its fields as keywords, not both."
        return wrapper

    return decorate
