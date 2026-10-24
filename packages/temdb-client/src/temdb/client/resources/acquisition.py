import builtins
from contextlib import AbstractAsyncContextManager
from datetime import datetime
from typing import Any, BinaryIO, Literal, overload

import httpx
from pydantic import BaseModel

from temdb.models import (
    AcquisitionCreate,
    AcquisitionFullMetadata,
    AcquisitionResponse,
    AcquisitionStatusFilter,
    AcquisitionUpdate,
    FileObjectRequest,
    FileObjectResponse,
    TileBulkDeleteResult,
    TileCreate,
    TileDeleteAllResult,
    TileResponse,
    TileUpdate,
)

from .base import BaseResource, accepts_keywords
from .image import ImageReader, ImageWriter, open_image, put_image


class PaginatedAcquisitionResponse(BaseModel):
    acquisitions: list[AcquisitionResponse]
    metadata: dict[str, Any]


class PaginatedTileResponse(BaseModel):
    tiles: list[TileResponse]
    metadata: dict[str, Any]


class AcquisitionResource(BaseResource):
    def __init__(self, *args, file_client: httpx.AsyncClient | None = None, **kwargs):
        self._file_client = file_client
        super().__init__(*args, **kwargs)

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
        status: AcquisitionStatusFilter | None = None,
        qc_state: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        fields: list[str] | None = None,
        **kwargs: Any,
    ) -> PaginatedAcquisitionResponse | dict[str, Any]:
        """List acquisitions with filtering, sorting, and pagination.

        With fields, the page is returned as the server sends it: each acquisition holds only those fields.
        """
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
            "status": status,
            "qc_state": qc_state,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "fields": fields,
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get("acquisitions", params=params)
        return response_data if fields else PaginatedAcquisitionResponse.model_validate(response_data)

    @accepts_keywords(AcquisitionCreate)
    async def create(self, acquisition_data: AcquisitionCreate) -> AcquisitionResponse:
        response_data = await self._post("acquisitions", data=acquisition_data.model_dump(exclude_unset=True))
        return AcquisitionResponse.model_validate(response_data)

    async def get(self, acquisition_id: str) -> AcquisitionResponse:
        response_data = await self._get(f"acquisitions/{acquisition_id}")
        return AcquisitionResponse.model_validate(response_data)

    @accepts_keywords(AcquisitionUpdate)
    async def update(self, acquisition_id: str, acquisition_data: AcquisitionUpdate) -> AcquisitionResponse:
        update_payload = acquisition_data.model_dump(exclude_unset=True)
        response_data = await self._patch(f"acquisitions/{acquisition_id}", data=update_payload)
        return AcquisitionResponse.model_validate(response_data)

    async def delete(self, acquisition_id: str) -> None:
        await self._delete(f"acquisitions/{acquisition_id}")

    @accepts_keywords(TileCreate)
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
        x_min: float | None = None,
        x_max: float | None = None,
        y_min: float | None = None,
        y_max: float | None = None,
    ) -> PaginatedTileResponse | dict[str, Any]:
        """Retrieve tiles for an acquisition with pagination."""
        endpoint = f"acquisitions/{acquisition_id}/tiles"
        params = {
            "limit": limit,
            "cursor": cursor,
            "fields": fields,
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response_data = await self._get(endpoint, params=params)
        return response_data if fields else PaginatedTileResponse.model_validate(response_data)

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

    @accepts_keywords(TileUpdate)
    async def update_tile(self, acquisition_id: str, tile_id: str, tile_data: TileUpdate) -> TileResponse:
        """Updates a tile from an acquisition."""
        endpoint = f"acquisitions/{acquisition_id}/tiles/{tile_id}"
        payload = tile_data.model_dump(exclude_unset=True)
        response_data = await self._patch(endpoint, data=payload)
        return TileResponse.model_validate(response_data)

    async def update_tiles_bulk(
        self, acquisition_id: str, tile_updates: dict[str, TileUpdate]
    ) -> builtins.list[TileResponse]:
        """Updates multiple tiles from an acquisition."""
        endpoint = f"acquisitions/{acquisition_id}/tiles/bulk"
        payload = {tile_id: tile_data.model_dump(exclude_unset=True) for tile_id, tile_data in tile_updates.items()}
        response_data = await self._patch(endpoint, data=payload)
        return [TileResponse.model_validate(tile) for tile in response_data]

    async def delete_tile(self, acquisition_id: str, tile_id: str) -> None:
        """Delete a specific tile from an acquisition.

        Raises TEMdbConflictError if the acquisition is marked 'complete'.
        """
        endpoint = f"acquisitions/{acquisition_id}/tiles/{tile_id}"
        await self._delete(endpoint)

    async def delete_all_tiles(self, acquisition_id: str) -> TileDeleteAllResult:
        """Deletes all tiles from an acquisition.

        Raises TEMdbConflictError if the acquisition is marked 'complete'.
        """
        endpoint = f"acquisitions/{acquisition_id}/tiles/all"
        return TileDeleteAllResult.model_validate(await self._request("DELETE", endpoint))

    async def delete_tiles_bulk(self, acquisition_id: str, tile_ids: builtins.list[str]) -> TileBulkDeleteResult:
        """Deletes the acquisition's tiles with these tile_ids; tile_ids not found in it are listed in not_found.

        Raises TEMdbConflictError if the acquisition is marked 'complete'.
        """
        endpoint = f"acquisitions/{acquisition_id}/tiles/bulk"
        return TileBulkDeleteResult.model_validate(await self._request("DELETE", endpoint, json=tile_ids))

    async def get_all_tiles(
        self, acquisition_id: str, *, page_limit: int = 1000, **kwargs
    ) -> builtins.list[TileResponse] | builtins.list[dict[str, Any]]:
        """Fetch every tile for an acquisition, auto-following cursor pagination."""
        all_tiles: builtins.list = []
        cursor: str | None = None
        while True:
            page = await self.get_tiles(acquisition_id, cursor=cursor, limit=page_limit, **kwargs)
            tiles, metadata = (
                (page["tiles"], page["metadata"]) if isinstance(page, dict) else (page.tiles, page.metadata)
            )
            all_tiles.extend(tiles)
            if not metadata.get("has_more"):
                break
            cursor = metadata.get("next_cursor")
            if cursor is None:
                break
        return all_tiles

    async def put_image_url(
        self, acquisition_id: str, tile_id: str, storage_location: FileObjectRequest | None = None
    ) -> FileObjectResponse:
        """Get a presigned URL for uploading an image for a specific tile."""
        endpoint = f"acquisitions/{acquisition_id}/tiles/{tile_id}/image"
        payload = storage_location.model_dump(exclude_unset=True) if storage_location else None
        response_data = await self._post(endpoint, data=payload)
        return FileObjectResponse.model_validate(response_data)

    async def put_image_urls(
        self, acquisition_id: str, tile_ids: builtins.list[str] | None = None, expiration: int | None = None
    ) -> builtins.dict[str, FileObjectResponse]:
        """Get presigned URLs for uploading images for multiple tiles.

        If tile_ids is None, presigned URLs will be generated for all tiles in the acquisition.
        """
        endpoint = f"acquisitions/{acquisition_id}/tiles/images"
        response_data = await self._post(
            endpoint, data=tile_ids, params={"expiration": expiration} if expiration else None
        )
        return {tile_id: FileObjectResponse.model_validate(response) for tile_id, response in response_data.items()}

    async def put_image(
        self,
        acquisition_id: str,
        tile_id: str,
        image_data: BinaryIO,
        storage_location: FileObjectRequest | None = None,
    ) -> FileObjectResponse:
        """Upload an open binary file directly and return its storage metadata."""
        location = await self.put_image_url(acquisition_id, tile_id, storage_location)
        return await put_image(location, image_data, self._file_client)

    @overload
    def open_image(
        self,
        acquisition_id: str,
        tile_id: str,
        mode: Literal["rb"] = "rb",
        storage_location: FileObjectRequest | None = None,
        expiration: int | None = None,
        *,
        size: int | None = None,
    ) -> AbstractAsyncContextManager[ImageReader]: ...

    @overload
    def open_image(
        self,
        acquisition_id: str,
        tile_id: str,
        mode: Literal["wb"],
        storage_location: FileObjectRequest | None = None,
        expiration: int | None = None,
        *,
        size: int,
    ) -> AbstractAsyncContextManager[ImageWriter]: ...

    def open_image(
        self,
        acquisition_id: str,
        tile_id: str,
        mode: str = "rb",
        storage_location: FileObjectRequest | None = None,
        expiration: int | None = None,
        *,
        size: int | None = None,
    ) -> AbstractAsyncContextManager[ImageReader | ImageWriter]:
        """Open an async binary stream; 'wb' requires the total byte size."""
        return open_image(
            lambda: (
                self.put_image_url(acquisition_id, tile_id, storage_location)
                if mode == "wb"
                else self.get_image_url(acquisition_id, tile_id, expiration)
            ),
            mode,
            size,
            self._file_client,
        )

    async def get_image(self, acquisition_id: str, tile_id: str, expiration: int | None = None) -> bytes:
        """Download the entire tile image into memory."""
        async with self.open_image(acquisition_id, tile_id, expiration=expiration) as image:
            return await image.read()

    async def get_image_url(
        self, acquisition_id: str, tile_id: str, expiration: int | None = None
    ) -> FileObjectResponse:
        """Get a presigned URL for downloading an image for a specific tile."""
        endpoint = f"acquisitions/{acquisition_id}/tiles/{tile_id}/image"
        response_data = await self._get(endpoint, params={"expiration": expiration} if expiration else None)
        return FileObjectResponse.model_validate(response_data)

    async def get_image_urls(
        self, acquisition_id: str, tile_ids: builtins.list[str] | None = None, expiration: int | None = None
    ) -> builtins.list[FileObjectResponse]:
        """Get presigned URLs for downloading images for multiple tiles.

        If tile_ids is None, presigned URLs will be generated for all tiles in the acquisition.
        """
        endpoint = f"acquisitions/{acquisition_id}/tiles/images"
        response_data = await self._get(
            endpoint, json=tile_ids, params={"expiration": expiration} if expiration else None
        )
        return {tile_id: FileObjectResponse.model_validate(response) for tile_id, response in response_data.items()}

    async def delete_image(self, acquisition_id: str, tile_id: str) -> None:
        """Delete the image for a specific tile."""
        endpoint = f"acquisitions/{acquisition_id}/tiles/{tile_id}/image"
        await self._delete(endpoint)

    async def delete_images(
        self, acquisition_id: str, tile_ids: builtins.list[str] | None = None
    ) -> builtins.list[str]:
        """Delete images for multiple tiles.

        If tile_ids is None, all images will be deleted for the acquisition.

        Returns a list of tile IDs for which images were successfully deleted.
        """
        endpoint = f"acquisitions/{acquisition_id}/tiles/images"
        return await self._delete(endpoint, json=tile_ids)

    async def get_complete_metadata(self, acquisition_id: str) -> dict[str, Any]:
        """Get complete metadata for an acquisition."""
        endpoint = f"acquisitions/{acquisition_id}/metadata"
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
        substrate_media_id: str | None = None,
        status: AcquisitionStatusFilter | None = None,
    ) -> dict[str, Any]:
        """List acquisitions with complete hierarchy metadata."""
        params = {
            "cursor": cursor,
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "specimen_id": specimen_id,
            "roi_id": roi_id,
            "acquisition_task_id": acquisition_task_id,
            "substrate_media_id": substrate_media_id,
            "status": status,
        }
        params = {k: v for k, v in params.items() if v is not None}
        return await self._get("aggregated/acquisitions", params=params)
