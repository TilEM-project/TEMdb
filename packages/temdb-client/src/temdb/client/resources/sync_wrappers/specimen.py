import builtins
from typing import Any

from temdb.models import (
    BlockResponse,
    SpecimenCreate,
    SpecimenResponse,
    SpecimenUpdate,
)

from ._base import SyncResourceBase


class SyncSpecimenResourceWrapper(SyncResourceBase):
    """Synchronous wrapper for the SpecimenResource."""

    def list(self, skip: int = 0, limit: int = 100, **kwargs: Any) -> list[SpecimenResponse]:
        return self._run(self._async_resource.list(skip=skip, limit=limit, **kwargs))

    def create(self, specimen_data: SpecimenCreate) -> SpecimenResponse:
        return self._run(self._async_resource.create(specimen_data))

    def get(self, specimen_id: str) -> SpecimenResponse:
        return self._run(self._async_resource.get(specimen_id))

    def update(self, specimen_id: str, specimen_data: SpecimenUpdate) -> SpecimenResponse:
        return self._run(self._async_resource.update(specimen_id, specimen_data))

    def delete(self, specimen_id: str) -> None:
        return self._run(self._async_resource.delete(specimen_id))

    def add_image(self, specimen_id: str, image_url: str) -> SpecimenResponse:
        return self._run(self._async_resource.add_image(specimen_id, image_url))

    def remove_image(self, specimen_id: str, image_url: str) -> SpecimenResponse:
        return self._run(self._async_resource.remove_image(specimen_id, image_url))

    def list_blocks(self, specimen_id: str, skip: int = 0, limit: int = 100) -> builtins.list[BlockResponse]:
        return self._run(self._async_resource.list_blocks(specimen_id, skip=skip, limit=limit))
