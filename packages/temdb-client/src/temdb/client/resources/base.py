import inspect
import logging
from collections.abc import Callable
from functools import wraps
from itertools import takewhile
from typing import Any


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
        await self._request("DELETE", endpoint, **kwargs)


def accepts_keywords(model):
    """Let a create/update method take the model's fields as keywords instead of a built model."""

    def decorate(method):
        parameters = list(inspect.signature(method).parameters)[1:]

        @wraps(method)
        async def wrapper(self, *args, **kwargs):
            leading = list(takewhile(kwargs.__contains__, parameters[len(args) :]))
            args = (*args, *(kwargs.pop(name) for name in leading))
            named = [key for key, value in kwargs.items() if isinstance(value, model)]
            if named:
                args = (*args, kwargs.pop(named[0]))
            if args and isinstance(args[-1], model):
                if kwargs:
                    raise TypeError(f"Pass a {model.__name__} or its fields as keywords, not both")
                return await method(self, *args)
            return await method(self, *args, model(**kwargs))

        wrapper.__doc__ = f"{method.__doc__ or ''}\n\nTakes a {model.__name__} or its fields as keywords, not both."
        return wrapper

    return decorate
