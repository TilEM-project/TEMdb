import inspect
import logging
from collections.abc import Callable
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
            size = limit or page_size
            records, has_more = await self._page(endpoint, params, skip or 0, size)
            return Page([model.model_validate(record) for record in records], has_more=has_more)
        everything: list[dict[str, Any]] = []
        previous_first = None
        for number in range(max_pages):
            records, has_more = await self._page(endpoint, params, number * page_size, page_size)
            if number and records and records[0] == previous_first:
                raise TEMdbClientError(f"{endpoint}: the server ignored skip and returned the same page again")
            everything += records
            if not has_more:
                return [model.model_validate(record) for record in everything]
            previous_first = records[0] if records else None
        raise TEMdbClientError(f"{endpoint}: more records remain after {max_pages} pages of {page_size}")

    async def _page(
        self, endpoint: str, params: dict[str, Any], skip: int, limit: int
    ) -> tuple[list[dict[str, Any]], bool]:
        data, headers = await self._get(endpoint, params={**params, "skip": skip, "limit": limit}, with_headers=True)
        records = data if isinstance(data, list) else []
        flag = headers.get(HAS_MORE_HEADER)
        return records, (flag == "true") if flag is not None else len(records) == limit


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
