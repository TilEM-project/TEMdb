import asyncio
import builtins
from typing import Any

from temdb.models import (
    BlockResponse,
    SpecimenCreate,
    SpecimenResponse,
    SpecimenUpdate,
)

from ..specimen import SpecimenResource


class SyncSpecimenResourceWrapper:
    """Synchronous wrapper for the SpecimenResource."""

    def __init__(self, async_resource: SpecimenResource):
        self._async_resource = async_resource

    def list(self, skip: int = 0, limit: int = 100, **kwargs: Any) -> list[SpecimenResponse]:
        """List specimens."""
        return asyncio.run(self._async_resource.list(skip=skip, limit=limit, **kwargs))

    def create(self, specimen_data: SpecimenCreate) -> SpecimenResponse:
        """Create a new specimen."""
        return asyncio.run(self._async_resource.create(specimen_data))

    def get(self, specimen_id: str) -> SpecimenResponse:
        """Get a specific specimen by ID."""
        return asyncio.run(self._async_resource.get(specimen_id))

    def update(self, specimen_id: str, specimen_data: SpecimenUpdate) -> SpecimenResponse:
        """Update an existing specimen."""
        return asyncio.run(self._async_resource.update(specimen_id, specimen_data))

    def delete(self, specimen_id: str) -> None:
        """Delete a specimen."""
        return asyncio.run(self._async_resource.delete(specimen_id))

    def add_image(self, specimen_id: str, image_url: str) -> SpecimenResponse:
        """Add an image URL to a specimen."""
        return asyncio.run(self._async_resource.add_image(specimen_id, image_url))

    def remove_image(self, specimen_id: str, image_url: str) -> SpecimenResponse:
        """Remove an image URL from a specimen."""
        return asyncio.run(self._async_resource.remove_image(specimen_id, image_url))

    def list_blocks(self, specimen_id: str, skip: int = 0, limit: int = 100) -> builtins.list[BlockResponse]:
        """List blocks associated with a specific specimen."""
        return asyncio.run(self._async_resource.list_blocks(specimen_id, skip=skip, limit=limit))
