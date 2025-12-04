import asyncio
import builtins
from datetime import datetime
from typing import Any

from temdb.models import (
    AcquisitionCreate,
    AcquisitionResponse,
    AcquisitionStatus,
    AcquisitionUpdate,
    StorageLocation,
    StorageLocationCreate,
    TileCreate,
    TileResponse,
)

from ..acquisition import (
    AcquisitionResource,
    PaginatedAcquisitionResponse,
    PaginatedTileResponse,
)


class SyncAcquisitionResourceWrapper:
    """Synchronous wrapper for the AcquisitionResource."""

    def __init__(self, async_resource: AcquisitionResource):
        self._async_resource = async_resource

    def list(
        self,
        cursor: str | None = None,
        limit: int = 50,
        sort_by: str = "start_time",
        sort_order: int = -1,
        specimen_id: str | None = None,
        roi_id: int | None = None,
        acquisition_task_id: str | None = None,
        montage_set_name: str | None = None,
        magnification: int | None = None,
        status: AcquisitionStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        fields: list[str] | None = None,
        **kwargs: Any,
    ) -> PaginatedAcquisitionResponse:
        """List acquisitions."""
        return asyncio.run(
            self._async_resource.list(
                cursor=cursor,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order,
                specimen_id=specimen_id,
                roi_id=roi_id,
                acquisition_task_id=acquisition_task_id,
                montage_set_name=montage_set_name,
                magnification=magnification,
                status=status,
                start_date=start_date,
                end_date=end_date,
                fields=fields,
                **kwargs,
            )
        )

    def create(self, acquisition_data: AcquisitionCreate) -> AcquisitionResponse:
        """Create a new acquisition."""
        return asyncio.run(self._async_resource.create(acquisition_data))

    def get(self, acquisition_id: str) -> AcquisitionResponse:
        """Get a specific acquisition by ID."""
        return asyncio.run(self._async_resource.get(acquisition_id))

    def update(self, acquisition_id: str, acquisition_data: AcquisitionUpdate) -> AcquisitionResponse:
        """Update an existing acquisition."""
        return asyncio.run(self._async_resource.update(acquisition_id, acquisition_data))

    def delete(self, acquisition_id: str) -> None:
        """Delete an acquisition."""
        return asyncio.run(self._async_resource.delete(acquisition_id))

    def add_tile(self, acquisition_id: str, tile_data: TileCreate) -> TileResponse:
        """Add a single tile to an acquisition."""
        return asyncio.run(self._async_resource.add_tile(acquisition_id, tile_data))

    def get_tiles(
        self,
        acquisition_id: str,
        cursor: str | None = None,
        limit: int = 100,
        fields: builtins.list[str] | None = None,
    ) -> PaginatedTileResponse:
        """Retrieve tiles for an acquisition."""
        return asyncio.run(self._async_resource.get_tiles(acquisition_id, cursor=cursor, limit=limit, fields=fields))

    def get_tile(self, acquisition_id: str, tile_id: str) -> TileResponse:
        """Get a specific tile."""
        return asyncio.run(self._async_resource.get_tile(acquisition_id, tile_id))

    def get_tile_count(self, acquisition_id: str) -> dict[str, int]:
        """Get the count of tiles."""
        return asyncio.run(self._async_resource.get_tile_count(acquisition_id))

    def add_tiles_bulk(self, acquisition_id: str, tiles_data: builtins.list[TileCreate]) -> dict[str, Any]:
        """Add multiple tiles in bulk."""
        return asyncio.run(self._async_resource.add_tiles_bulk(acquisition_id, tiles_data))

    def delete_tile(self, acquisition_id: str, tile_id: str) -> None:
        """Delete a specific tile."""
        return asyncio.run(self._async_resource.delete_tile(acquisition_id, tile_id))

    def add_storage_location(self, acquisition_id: str, location_data: StorageLocationCreate) -> AcquisitionResponse:
        """Add a storage location."""
        return asyncio.run(self._async_resource.add_storage_location(acquisition_id, location_data))

    def get_current_storage_location(self, acquisition_id: str) -> StorageLocation | None:
        """Get the current storage location."""
        return asyncio.run(self._async_resource.get_current_storage_location(acquisition_id))

    def get_minimap_uri(self, acquisition_id: str) -> dict[str, str | None]:
        """Get the minimap URI."""
        return asyncio.run(self._async_resource.get_minimap_uri(acquisition_id))
