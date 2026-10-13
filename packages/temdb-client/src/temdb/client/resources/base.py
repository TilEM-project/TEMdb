import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from pydantic import ValidationError


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
        @wraps(method)
        async def wrapper(self, *args, **kwargs):
            named = [key for key, value in kwargs.items() if isinstance(value, model)]
            if named:
                args = (*args, kwargs.pop(named[0]))
            if args and isinstance(args[-1], model):
                if kwargs:
                    raise TypeError(f"Pass a {model.__name__} or its fields as keywords, not both")
                return await method(self, *args)
            built = model(**kwargs)
            if built.model_extra:
                raise ValidationError.from_exception_data(
                    model.__name__,
                    [
                        {"type": "extra_forbidden", "loc": (key,), "input": value}
                        for key, value in built.model_extra.items()
                    ],
                )
            return await method(self, *args, built)

        wrapper.__doc__ = f"{method.__doc__ or ''}\n\nTakes a {model.__name__} or its fields as keywords, not both."
        return wrapper

    return decorate
