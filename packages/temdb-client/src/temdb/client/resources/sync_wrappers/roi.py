from typing import Any

from temdb.models import (
    ROIChildrenResponse,
    ROICreate,
    ROIResponse,
    ROIUpdate,
)

from ._base import SyncResourceBase


class SyncROIResourceWrapper(SyncResourceBase):
    """Synchronous wrapper for the ROIResource."""

    def list_by_section(self, section_id: str, skip: int = 0, limit: int = 100, **kwargs: Any) -> list[ROIResponse]:
        return self._run(self._async_resource.list_by_section(section_id, skip=skip, limit=limit, **kwargs))

    def list_all(
        self,
        specimen_id: str | None = None,
        block_id: str | None = None,
        cutting_session_id: str | None = None,
        section_id: str | None = None,
        is_parent_roi: bool | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[ROIResponse]:
        return self._run(
            self._async_resource.list_all(
                specimen_id=specimen_id,
                block_id=block_id,
                cutting_session_id=cutting_session_id,
                section_id=section_id,
                is_parent_roi=is_parent_roi,
                skip=skip,
                limit=limit,
                **kwargs,
            )
        )

    def create(self, roi_data: ROICreate) -> ROIResponse:
        return self._run(self._async_resource.create(roi_data))

    def get(self, roi_id: int) -> ROIResponse:
        return self._run(self._async_resource.get(roi_id))

    def update(self, roi_id: int, roi_data: ROIUpdate) -> ROIResponse:
        return self._run(self._async_resource.update(roi_id, roi_data))

    def delete(self, roi_id: int) -> None:
        return self._run(self._async_resource.delete(roi_id))

    def get_children(self, roi_id: int, skip: int = 0, limit: int = 10) -> ROIChildrenResponse:
        return self._run(self._async_resource.get_children(roi_id, skip=skip, limit=limit))
