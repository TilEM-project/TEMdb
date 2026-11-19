from typing import Any

from temdb.models import (
    AcquisitionResponse,
    AcquisitionStatusFilter,
    ROICreate,
    ROIResponse,
    ROIUpdate,
)

from .base import BaseResource, Page, accepts_keywords, without_none


class ROIResource(BaseResource):
    """Resource class for interacting with ROI endpoints."""

    async def list_by_section(
        self,
        section_id: str,
        cursor: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> list[ROIResponse]:
        """List ROIs associated with a specific section."""
        endpoint = f"sections/{section_id}/rois"
        params = dict(kwargs)
        return await self._list(endpoint, ROIResponse, params, cursor=cursor, offset=offset, limit=limit)

    async def list_all(
        self,
        specimen_id: str | None = None,
        block_id: str | None = None,
        cutting_session_id: str | None = None,
        section_id: str | None = None,
        is_parent_roi: bool | None = None,
        cursor: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> list[ROIResponse]:
        """List all ROIs, optionally filtering."""
        endpoint = "rois"
        params = without_none(
            specimen_id=specimen_id,
            block_id=block_id,
            cutting_session_id=cutting_session_id,
            section_id=section_id,
            is_parent_roi=is_parent_roi,
            **kwargs,
        )
        return await self._list(endpoint, ROIResponse, params, cursor=cursor, offset=offset, limit=limit)

    @accepts_keywords(ROICreate)
    async def create(self, roi_data: ROICreate) -> ROIResponse:
        """Create a new ROI."""
        response_data = await self._post("rois", data=roi_data.model_dump(exclude_unset=True))
        return ROIResponse.model_validate(response_data)

    async def get(self, roi_id: str) -> ROIResponse:
        """Get a specific ROI by its roi_id."""
        response_data = await self._get(f"rois/{roi_id}")
        return ROIResponse.model_validate(response_data)

    @accepts_keywords(ROIUpdate)
    async def update(self, roi_id: str, roi_data: ROIUpdate) -> ROIResponse:
        """Update an existing ROI."""
        update_payload = roi_data.model_dump(exclude_unset=True)
        response_data = await self._patch(f"rois/{roi_id}", data=update_payload)
        return ROIResponse.model_validate(response_data)

    async def delete(self, roi_id: str) -> None:
        """Delete an ROI."""
        await self._delete(f"rois/{roi_id}")

    async def get_children(
        self, roi_id: str, cursor: str | None = None, offset: int | None = None, limit: int | None = None
    ) -> list[ROIResponse] | Page:
        """Get the child ROIs of a parent ROI."""
        return await self._list(f"rois/{roi_id}/children", ROIResponse, {}, cursor=cursor, offset=offset, limit=limit)

    async def list_acquisitions(
        self, roi_id: str, *, status: AcquisitionStatusFilter | None = None, qc_state: str | None = None
    ) -> list[AcquisitionResponse]:
        """List every acquisition of an ROI (optionally filtered by status / qc_state)."""
        params = without_none(roi_id=roi_id, status=status, qc_state=qc_state)
        return await self._list("acquisitions", AcquisitionResponse, params, cursor=None, offset=None, limit=None)
