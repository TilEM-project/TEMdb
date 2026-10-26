from contextlib import AbstractAsyncContextManager
from typing import Any, BinaryIO, Literal, overload

import httpx

from temdb.models import (
    FileObjectRequest,
    FileObjectResponse,
    SectionCreate,
    SectionQuality,
    SectionResponse,
    SectionUpdate,
)

from .base import BaseResource, accepts_keywords
from .image import ImageReader, ImageWriter, open_image, put_image


class SectionResource(BaseResource):
    """Resource class for interacting with Section endpoints."""

    def __init__(self, *args, file_client: httpx.AsyncClient | None = None, **kwargs):
        self._file_client = file_client
        super().__init__(*args, **kwargs)

    async def list_by_session(
        self, cutting_session_id: str, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> list[SectionResponse]:
        """List sections associated with a specific cutting session."""
        endpoint = f"sections/sessions/{cutting_session_id}"
        params = {"skip": skip, "limit": limit}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return (
            [SectionResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []
        )

    async def list_all(
        self,
        specimen_id: str | None = None,
        block_id: str | None = None,
        cutting_session_id: str | None = None,
        media_id: str | None = None,
        quality: SectionQuality | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[SectionResponse]:
        """List all sections, optionally filtering."""
        endpoint = "sections"
        params = {
            "specimen_id": specimen_id,
            "block_id": block_id,
            "cutting_session_id": cutting_session_id,
            "media_id": media_id,
            "quality": (quality.value if quality else None),
            "skip": skip,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return (
            [SectionResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []
        )

    @accepts_keywords(SectionCreate)
    async def create(self, section_data: SectionCreate) -> SectionResponse:
        """Create a new section."""
        response_data = await self._post("sections", data=section_data.model_dump(mode="json", exclude_unset=True))
        return SectionResponse.model_validate(response_data)

    async def get(self, section_id: str) -> SectionResponse:
        """Get a section by its section_id."""
        response_data = await self._get(f"sections/{section_id}")
        return SectionResponse.model_validate(response_data)

    @accepts_keywords(FileObjectRequest)
    async def put_image_url(
        self, section_id: str, name: str, storage_location: FileObjectRequest | None = None
    ) -> FileObjectResponse:
        """Get a presigned URL for uploading a named image of a section."""
        endpoint = f"sections/{section_id}/images/{name}"
        payload = storage_location.model_dump(exclude_unset=True) if storage_location else None
        response_data = await self._post(endpoint, data=payload)
        return FileObjectResponse.model_validate(response_data)

    async def put_image(
        self,
        section_id: str,
        name: str,
        image_data: BinaryIO,
        storage_location: FileObjectRequest | None = None,
        **kwargs: Any,
    ) -> FileObjectResponse:
        """Upload an open binary file directly and return its storage metadata."""
        location = (
            await self.put_image_url(section_id, name, **kwargs)
            if storage_location is None and kwargs
            else await self.put_image_url(section_id, name, storage_location=storage_location, **kwargs)
        )
        return await put_image(location, image_data, self._file_client)

    @overload
    def open_image(
        self,
        section_id: str,
        name: str,
        mode: Literal["rb"] = "rb",
        storage_location: FileObjectRequest | None = None,
        expiration: int | None = None,
        *,
        size: int | None = None,
    ) -> AbstractAsyncContextManager[ImageReader]: ...

    @overload
    def open_image(
        self,
        section_id: str,
        name: str,
        mode: Literal["wb"],
        storage_location: FileObjectRequest | None = None,
        expiration: int | None = None,
        *,
        size: int,
    ) -> AbstractAsyncContextManager[ImageWriter]: ...

    def open_image(
        self,
        section_id: str,
        name: str,
        mode: str = "rb",
        storage_location: FileObjectRequest | None = None,
        expiration: int | None = None,
        *,
        size: int | None = None,
    ) -> AbstractAsyncContextManager[ImageReader | ImageWriter]:
        """Open an async binary stream; 'wb' requires the total byte size."""
        return open_image(
            lambda: (
                self.put_image_url(section_id, name, storage_location)
                if mode == "wb"
                else self.get_image_url(section_id, name, expiration)
            ),
            mode,
            size,
            self._file_client,
        )

    async def get_image_url(self, section_id: str, name: str, expiration: int | None = None) -> FileObjectResponse:
        """Get a presigned URL for downloading a named image of a section."""
        endpoint = f"sections/{section_id}/images/{name}"
        response_data = await self._get(endpoint, params={"expiration": expiration} if expiration else None)
        return FileObjectResponse.model_validate(response_data)

    async def get_image(self, section_id: str, name: str, expiration: int | None = None) -> bytes:
        """Download a named section image into memory."""
        async with self.open_image(section_id, name, expiration=expiration) as image:
            return await image.read()

    async def delete_image(self, section_id: str, name: str) -> None:
        """Delete a named image of a section."""
        endpoint = f"sections/{section_id}/images/{name}"
        await self._delete(endpoint)

    @accepts_keywords(SectionUpdate)
    async def update(self, section_id: str, section_data: SectionUpdate) -> SectionResponse:
        """Update a section by its section_id."""
        update_payload = section_data.model_dump(exclude_unset=True)
        response_data = await self._patch(f"sections/{section_id}", data=update_payload)
        return SectionResponse.model_validate(response_data)

    async def delete(self, section_id: str) -> None:
        """Delete a section by its section_id."""
        await self._delete(f"sections/{section_id}")

    async def list_by_block(
        self, block_id: str, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> list[SectionResponse]:
        """List sections associated with a specific block."""
        endpoint = f"sections/blocks/{block_id}"
        params = {"skip": skip, "limit": limit}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return (
            [SectionResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []
        )

    async def list_by_specimen(
        self, specimen_id: str, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> list[SectionResponse]:
        """List sections associated with a specific specimen."""
        endpoint = f"sections/specimens/{specimen_id}"
        params = {"skip": skip, "limit": limit}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return (
            [SectionResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []
        )

    async def list_by_media(
        self,
        media_id: str,
        skip: int = 0,
        limit: int = 100,
        relative_position: int | None = None,
        **kwargs: Any,
    ) -> list[SectionResponse]:
        """List sections by media ID."""
        endpoint = f"sections/media/{media_id}"
        params = {"skip": skip, "limit": limit, "relative_position": relative_position}
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return (
            [SectionResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []
        )
