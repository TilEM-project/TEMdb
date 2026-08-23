import logging
from collections.abc import Callable
from functools import wraps
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


def kwargs2model(model):
    def model_wrapper(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if isinstance(args[-1], model):
                assert not kwargs, f"If a {model.__name__} object is provided, no keyword arguments may be provided!"
                return await func(*args)
            return await func(*args, model(**kwargs))

        return wrapper

    return model_wrapper
