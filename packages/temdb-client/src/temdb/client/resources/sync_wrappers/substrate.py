import builtins
from typing import Any

from temdb.models import (
    SectionResponse,
    SubstrateCreate,
    SubstrateResponse,
    SubstrateUpdate,
)

from ._base import SyncResourceBase


class SyncSubstrateResourceWrapper(SyncResourceBase):
    """Synchronous wrapper for the SubstrateResource."""

    def list(
        self,
        media_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[SubstrateResponse]:
        return self._run(
            self._async_resource.list(media_type=media_type, status=status, skip=skip, limit=limit, **kwargs)
        )

    def create(self, substrate_data: SubstrateCreate) -> SubstrateResponse:
        return self._run(self._async_resource.create(substrate_data))

    def get(self, media_id: str) -> SubstrateResponse:
        return self._run(self._async_resource.get(media_id))

    def update(self, media_id: str, substrate_data: SubstrateUpdate) -> SubstrateResponse:
        return self._run(self._async_resource.update(media_id, substrate_data))

    def delete(self, media_id: str) -> None:
        return self._run(self._async_resource.delete(media_id))

    def list_related_sections(self, media_id: str, skip: int = 0, limit: int = 100) -> builtins.list[SectionResponse]:
        return self._run(self._async_resource.list_related_sections(media_id, skip=skip, limit=limit))
