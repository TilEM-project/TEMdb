from typing import Any

from temdb.models import (
    SectionCreate,
    SectionQuality,
    SectionResponse,
    SectionUpdate,
)

from ._base import SyncResourceBase


class SyncSectionResourceWrapper(SyncResourceBase):
    """Synchronous wrapper for the SectionResource."""

    def list_by_session(
        self, cutting_session_id: str, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> list[SectionResponse]:
        return self._run(self._async_resource.list_by_session(cutting_session_id, skip=skip, limit=limit, **kwargs))

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
        return self._run(
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
        return self._run(self._async_resource.create(section_data))

    def get(self, cutting_session_id: str, section_id: str) -> SectionResponse:
        return self._run(self._async_resource.get(cutting_session_id, section_id))

    def update(self, cutting_session_id: str, section_id: str, section_data: SectionUpdate) -> SectionResponse:
        return self._run(self._async_resource.update(cutting_session_id, section_id, section_data))

    def delete(self, cutting_session_id: str, section_id: str) -> None:
        return self._run(self._async_resource.delete(cutting_session_id, section_id))

    def list_by_block(self, block_id: str, skip: int = 0, limit: int = 100, **kwargs: Any) -> list[SectionResponse]:
        return self._run(self._async_resource.list_by_block(block_id, skip=skip, limit=limit, **kwargs))

    def list_by_specimen(
        self, specimen_id: str, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> list[SectionResponse]:
        return self._run(self._async_resource.list_by_specimen(specimen_id, skip=skip, limit=limit, **kwargs))

    def list_by_media(
        self,
        media_id: str,
        skip: int = 0,
        limit: int = 100,
        relative_position: int | None = None,
        **kwargs: Any,
    ) -> list[SectionResponse]:
        return self._run(
            self._async_resource.list_by_media(
                media_id,
                skip=skip,
                limit=limit,
                relative_position=relative_position,
                **kwargs,
            )
        )

    def list_by_barcode(self, barcode: str, skip: int = 0, limit: int = 100, **kwargs: Any) -> list[SectionResponse]:
        return self._run(self._async_resource.list_by_barcode(barcode, skip=skip, limit=limit, **kwargs))
