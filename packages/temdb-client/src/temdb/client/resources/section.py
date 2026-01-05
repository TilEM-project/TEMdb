from typing import Any

from temdb.models import (
    SectionCreate,
    SectionQuality,
    SectionResponse,
    SectionUpdate,
)

from .base import BaseResource


class SectionResource(BaseResource):
    """Resource class for interacting with Section endpoints."""

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

    async def create(self, section_data: SectionCreate) -> SectionResponse:
        """Create a new section."""
        response_data = await self._post("sections", data=section_data.model_dump(mode="json", exclude_unset=True))
        return SectionResponse.model_validate(response_data)

    async def get(self, cutting_session_id: str, section_id: str) -> SectionResponse:
        """Get a specific section by session and section ID."""
        endpoint = f"sections/sessions/{cutting_session_id}/sections/{section_id}"
        response_data = await self._get(endpoint)
        return SectionResponse.model_validate(response_data)

    async def update(self, cutting_session_id: str, section_id: str, section_data: SectionUpdate) -> SectionResponse:
        """Update an existing section."""
        endpoint = f"sections/sessions/{cutting_session_id}/sections/{section_id}"
        update_payload = section_data.model_dump(exclude_unset=True)
        response_data = await self._patch(endpoint, data=update_payload)
        return SectionResponse.model_validate(response_data)

    async def delete(self, cutting_session_id: str, section_id: str) -> None:
        """Delete a section."""
        endpoint = f"sections/sessions/{cutting_session_id}/sections/{section_id}"
        await self._delete(endpoint)

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

    async def list_by_barcode(
        self, barcode: str, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> list[SectionResponse]:
        """List sections by barcode."""
        endpoint = f"sections/barcode/{barcode}"
        params = {"skip": skip, "limit": limit}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return (
            [SectionResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []
        )
