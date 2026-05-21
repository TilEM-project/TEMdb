from typing import Any

from temdb.models import (
    BlockCreate,
    BlockResponse,
    BlockUpdate,
    CuttingSessionResponse,
)

from ._base import SyncResourceBase


class SyncBlockResourceWrapper(SyncResourceBase):
    """Synchronous wrapper for the BlockResource."""

    def list_by_specimen(self, specimen_id: str, skip: int = 0, limit: int = 100, **kwargs: Any) -> list[BlockResponse]:
        return self._run(self._async_resource.list_by_specimen(specimen_id, skip=skip, limit=limit, **kwargs))

    def list_all(
        self,
        specimen_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[BlockResponse]:
        return self._run(self._async_resource.list_all(specimen_id=specimen_id, skip=skip, limit=limit, **kwargs))

    def create(self, block_data: BlockCreate) -> BlockResponse:
        return self._run(self._async_resource.create(block_data))

    def get(self, specimen_id: str, block_id: str) -> BlockResponse:
        return self._run(self._async_resource.get(specimen_id, block_id))

    def update(self, specimen_id: str, block_id: str, block_data: BlockUpdate) -> BlockResponse:
        return self._run(self._async_resource.update(specimen_id, block_id, block_data))

    def delete(self, specimen_id: str, block_id: str) -> None:
        return self._run(self._async_resource.delete(specimen_id, block_id))

    def get_cut_sessions(
        self, specimen_id: str, block_id: str, skip: int = 0, limit: int = 100
    ) -> list[CuttingSessionResponse]:
        return self._run(self._async_resource.get_cut_sessions(specimen_id, block_id, skip=skip, limit=limit))
