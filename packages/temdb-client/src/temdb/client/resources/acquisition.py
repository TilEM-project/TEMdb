import builtins
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from temdb.models import (
    AcquisitionCreate,
    AcquisitionFullMetadata,
    AcquisitionResponse,
    AcquisitionStatus,
    AcquisitionUpdate,
    StorageLocation,
    StorageLocationCreate,
    TileCreate,
    TileResponse,
)

from .base import BaseResource


class PaginatedAcquisitionResponse(BaseModel):
    acquisitions: list[AcquisitionResponse]
    metadata: dict[str, Any]


class PaginatedTileResponse(BaseModel):
    tiles: list[TileResponse]
    metadata: dict[str, Any]


class AcquisitionResource(BaseResource):
    async def list(
        self,
        cursor: str | None = None,
        limit: int = 50,
        sort_by: str = "start_time",
        sort_order: int = -1,
        specimen_id: str | None = None,
        roi_id: str | None = None,
        acquisition_task_id: str | None = None,
        montage_set_name: str | None = None,
        magnification: int | None = None,
        status: AcquisitionStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        fields: list[str] | None = None,
        **kwargs: Any,
    ) -> PaginatedAcquisitionResponse:
        """List acquisitions with filtering, sorting, and pagination."""
        params = {
            "cursor": cursor,
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "specimen_id": specimen_id,
            "roi_id": roi_id,
            "acquisition_task_id": acquisition_task_id,
            "montage_set_name": montage_set_name,
            "magnification": magnification,
            "status": status.value if status else None,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "fields": fields,
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get("acquisitions", params=params)
        return PaginatedAcquisitionResponse.model_validate(response_data)

    async def create(self, acquisition_data: AcquisitionCreate) -> AcquisitionResponse:
        response_data = await self._post("acquisitions", data=acquisition_data.model_dump(exclude_unset=True))
        return AcquisitionResponse.model_validate(response_data)

    async def get(self, acquisition_id: str) -> AcquisitionResponse:
        response_data = await self._get(f"acquisitions/{acquisition_id}")
        return AcquisitionResponse.model_validate(response_data)

    async def update(self, acquisition_id: str, acquisition_data: AcquisitionUpdate) -> AcquisitionResponse:
        update_payload = acquisition_data.model_dump(exclude_unset=True)
        response_data = await self._patch(f"acquisitions/{acquisition_id}", data=update_payload)
        return AcquisitionResponse.model_validate(response_data)

    async def delete(self, acquisition_id: str) -> None:
        await self._delete(f"acquisitions/{acquisition_id}")

    async def add_tile(self, acquisition_id: str, tile_data: TileCreate) -> TileResponse:
        response_data = await self._post(
            f"acquisitions/{acquisition_id}/tiles",
            data=tile_data.model_dump(exclude_unset=True),
        )
        return TileResponse.model_validate(response_data)

    async def get_tiles(
        self,
        acquisition_id: str,
        cursor: str | None = None,
        limit: int = 100,
        fields: builtins.list[str] | None = None,
    ) -> PaginatedTileResponse:
        """Retrieve tiles for an acquisition with pagination."""
        endpoint = f"acquisitions/{acquisition_id}/tiles"
        params = {"limit": limit, "cursor": cursor, "fields": fields}
        params = {k: v for k, v in params.items() if v is not None}
        response_data = await self._get(endpoint, params=params)
        return PaginatedTileResponse.model_validate(response_data)

    async def get_tile(self, acquisition_id: str, tile_id: str) -> TileResponse:
        """Get a specific tile by ID within an acquisition."""
        response_data = await self._get(f"acquisitions/{acquisition_id}/tiles/{tile_id}")
        return TileResponse.model_validate(response_data)

    async def get_tile_count(self, acquisition_id: str) -> dict[str, int]:
        """Get the count of tiles for an acquisition."""
        return await self._get(f"acquisitions/{acquisition_id}/tile-count")

    async def add_tiles_bulk(self, acquisition_id: str, tiles_data: builtins.list[TileCreate]) -> dict[str, Any]:
        """Add multiple tiles to an acquisition in bulk."""
        endpoint = f"acquisitions/{acquisition_id}/tiles/bulk"
        payload = [tile.model_dump(exclude_unset=True) for tile in tiles_data]
        return await self._post(endpoint, data=payload)

    async def delete_tile(self, acquisition_id: str, tile_id: str) -> None:
        """Delete a specific tile from an acquisition."""
        endpoint = f"acquisitions/{acquisition_id}/tiles/{tile_id}"
        await self._delete(endpoint)

    async def add_storage_location(
        self, acquisition_id: str, location_data: StorageLocationCreate
    ) -> AcquisitionResponse:
        """Add a storage location to an acquisition. Returns the updated acquisition."""
        endpoint = f"acquisitions/{acquisition_id}/storage-locations"
        response_data = await self._post(endpoint, data=location_data.model_dump(exclude_unset=True))
        return AcquisitionResponse.model_validate(response_data)

    async def get_current_storage_location(self, acquisition_id: str) -> StorageLocation | None:
        """Get the current storage location for an acquisition."""
        endpoint = f"acquisitions/{acquisition_id}/current-storage"
        response_data = await self._get(endpoint)
        return StorageLocation.model_validate(response_data) if response_data else None

    async def get_minimap_uri(self, acquisition_id: str) -> dict[str, str | None]:
        """Get the calculated URI for the acquisition's minimap."""
        endpoint = f"acquisitions/{acquisition_id}/minimap-uri"
        return await self._get(endpoint)

    async def get_complete_metadata(self, acquisition_id: str) -> dict[str, Any]:
        """Get complete metadata for an acquisition."""
        endpoint = f"acquisitions/{acquisition_id}/complete-metadata"
        response_data = await self._get(endpoint)
        return response_data if isinstance(response_data, dict) else {}

    async def get_with_full_metadata(self, acquisition_id: str) -> AcquisitionFullMetadata:
        """Get acquisition with complete hierarchy metadata including substrate."""
        endpoint = f"acquisitions/{acquisition_id}/metadata"
        response_data = await self._get(endpoint)
        return AcquisitionFullMetadata.model_validate(response_data)

    async def list_with_full_metadata(
        self,
        cursor: str | None = None,
        limit: int = 50,
        sort_by: str = "start_time",
        sort_order: int = -1,
        specimen_id: str | None = None,
        roi_id: str | None = None,
        acquisition_task_id: str | None = None,
        montage_set_name: str | None = None,
        magnification: int | None = None,
        status: AcquisitionStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """List acquisitions with complete hierarchy metadata using MongoDB aggregation."""
        params = {
            "cursor": cursor,
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "specimen_id": specimen_id,
            "roi_id": roi_id,
            "acquisition_task_id": acquisition_task_id,
            "montage_set_name": montage_set_name,
            "magnification": magnification,
            "status": status.value if status else None,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        return await self._get("acquisitions/aggregated", params=params)
