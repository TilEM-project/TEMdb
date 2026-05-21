import asyncio
from collections.abc import Coroutine
from typing import Any


class SyncResourceBase:
    def __init__(self, async_resource: Any, loop: asyncio.AbstractEventLoop):
        self._async_resource = async_resource
        self._loop = loop

    def _run(self, coro: Coroutine[Any, Any, Any]) -> Any:
        return asyncio.run_coroutine_threadsafe(coro, self._loop).result()
