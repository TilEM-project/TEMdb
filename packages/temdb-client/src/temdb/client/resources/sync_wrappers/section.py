import asyncio
from typing import Any

from temdb.models import (
    SectionCreate,
    SectionQuality,
    SectionResponse,
    SectionUpdate,
)

from ..section import SectionResource


class SyncSectionResourceWrapper:
    """Synchronous wrapper for the SectionResource."""

    def __init__(self, async_resource: SectionResource):
        self._async_resource = async_resource

    def list_by_session(
        self, cutting_session_id: str, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> list[SectionResponse]:
        """List sections associated with a specific cutting session."""
        return asyncio.run(self._async_resource.list_by_session(cutting_session_id, skip=skip, limit=limit, **kwargs))

    def list_all(
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
        return asyncio.run(
            self._async_resource.list_all(
                specimen_id=specimen_id,
                block_id=block_id,
                cutting_session_id=cutting_session_id,
                media_id=media_id,
                quality=quality,
                skip=skip,
                limit=limit,
                **kwargs,
            )
        )

    def create(self, section_data: SectionCreate) -> SectionResponse:
        """Create a new section."""
        return asyncio.run(self._async_resource.create(section_data))

    def get(self, cutting_session_id: str, section_id: str) -> SectionResponse:
        """Get a specific section by session and section ID."""
        return asyncio.run(self._async_resource.get(cutting_session_id, section_id))

    def update(self, cutting_session_id: str, section_id: str, section_data: SectionUpdate) -> SectionResponse:
        """Update an existing section."""
        return asyncio.run(self._async_resource.update(cutting_session_id, section_id, section_data))

    def delete(self, cutting_session_id: str, section_id: str) -> None:
        """Delete a section."""
        return asyncio.run(self._async_resource.delete(cutting_session_id, section_id))

    def list_by_block(self, block_id: str, skip: int = 0, limit: int = 100, **kwargs: Any) -> list[SectionResponse]:
        """List sections associated with a specific block."""
        return asyncio.run(self._async_resource.list_by_block(block_id, skip=skip, limit=limit, **kwargs))

    def list_by_specimen(
        self, specimen_id: str, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> list[SectionResponse]:
        """List sections associated with a specific specimen."""
        return asyncio.run(self._async_resource.list_by_specimen(specimen_id, skip=skip, limit=limit, **kwargs))

    def list_by_media(
        self,
        media_id: str,
        skip: int = 0,
        limit: int = 100,
        relative_position: int | None = None,
        **kwargs: Any,
    ) -> list[SectionResponse]:
        """List sections by media ID."""
        return asyncio.run(
            self._async_resource.list_by_media(
                media_id,
                skip=skip,
                limit=limit,
                relative_position=relative_position,
                **kwargs,
            )
        )

    def list_by_barcode(self, barcode: str, skip: int = 0, limit: int = 100, **kwargs: Any) -> list[SectionResponse]:
        """List sections by barcode."""
        return asyncio.run(self._async_resource.list_by_barcode(barcode, skip=skip, limit=limit, **kwargs))
