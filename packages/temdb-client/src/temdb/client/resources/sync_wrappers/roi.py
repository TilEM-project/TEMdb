import asyncio
from typing import Any

from temdb.models import (
    ROIChildrenResponse,
    ROICreate,
    ROIResponse,
    ROIUpdate,
)

from ..roi import ROIResource


class SyncROIResourceWrapper:
    """Synchronous wrapper for the ROIResource."""

    def __init__(self, async_resource: ROIResource):
        self._async_resource = async_resource

    def list_by_section(self, section_id: str, skip: int = 0, limit: int = 100, **kwargs: Any) -> list[ROIResponse]:
        """List ROIs associated with a specific section."""
        return asyncio.run(self._async_resource.list_by_section(section_id, skip=skip, limit=limit, **kwargs))

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
        """List all ROIs, optionally filtering."""
        return asyncio.run(
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
        """Create a new ROI."""
        return asyncio.run(self._async_resource.create(roi_data))

    def get(self, roi_id: int) -> ROIResponse:
        """Get a specific ROI by its integer ID."""
        return asyncio.run(self._async_resource.get(roi_id))

    def update(self, roi_id: int, roi_data: ROIUpdate) -> ROIResponse:
        """Update an existing ROI."""
        return asyncio.run(self._async_resource.update(roi_id, roi_data))

    def delete(self, roi_id: int) -> None:
        """Delete an ROI."""
        return asyncio.run(self._async_resource.delete(roi_id))

    def get_children(self, roi_id: int, skip: int = 0, limit: int = 10) -> ROIChildrenResponse:
        """Get child ROIs for a specific parent ROI."""
        return asyncio.run(self._async_resource.get_children(roi_id, skip=skip, limit=limit))
