import inspect
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from functools import wraps
from itertools import takewhile
from typing import Any, TypeVar

from temdb.models import Page as PageBody

from ..exceptions import TEMdbClientError

T = TypeVar("T")


class Page(list):
    """One page of records: a list that also carries the next page's cursor and the number of matching records."""

    def __init__(self, items=(), next_cursor: str | None = None, total: int = 0):
        super().__init__(items)
        self.next_cursor = next_cursor
        self.total = total

    @property
    def items(self) -> list:
        return self


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
        self, fetch: Callable[[str | None], Awaitable[Any]], *, max_pages: int = 10_000
    ) -> AsyncIterator[Any]:
        """Yield fetch(cursor) page by page, following each page's next_cursor until it is None."""
        cursor = None
        for _ in range(max_pages):
            page = await fetch(cursor)
            yield page
            if page.next_cursor is None:
                return
            if page.next_cursor == cursor:
                raise TEMdbClientError("the server returned the same page again")
            cursor = page.next_cursor
        raise TEMdbClientError(f"more pages remain after {max_pages} pages")

    async def _page(
        self, endpoint: str, model: type[T] | None, params: dict[str, Any], *, cursor, offset, limit
    ) -> Page:
        query = {**params, **without_none(cursor=cursor, offset=offset, limit=limit)}
        body = PageBody[model or dict[str, Any]].model_validate(await self._get(endpoint, params=query))
        return Page(body.items, body.next_cursor, body.total)

    async def _list(
        self,
        endpoint: str,
        model: type[T] | None,
        params: dict[str, Any],
        *,
        cursor: str | None,
        offset: int | None,
        limit: int | None,
        page_size: int = 100,
        max_pages: int = 10_000,
    ) -> list[T] | Page:
        """One page when cursor, offset or limit is given, otherwise every row."""
        if cursor is not None or offset is not None or limit is not None:
            return await self._page(endpoint, model, params, cursor=cursor, offset=offset, limit=limit or page_size)
        pages = self._pages(
            lambda cursor: self._page(endpoint, model, params, cursor=cursor, offset=None, limit=page_size),
            max_pages=max_pages,
        )
        return [item async for page in pages for item in page.items]


def without_none(**values: Any) -> dict[str, Any]:
    """The keyword arguments whose value is not None, for building query parameters."""
    return {key: value for key, value in values.items() if value is not None}


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
