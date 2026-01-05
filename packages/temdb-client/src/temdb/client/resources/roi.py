from typing import Any

from temdb.models import (
    ROIChildrenResponse,
    ROICreate,
    ROIResponse,
    ROIUpdate,
)

from .base import BaseResource


class ROIResource(BaseResource):
    """Resource class for interacting with ROI endpoints."""

    async def list_by_section(
        self, section_id: str, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> list[ROIResponse]:
        """List ROIs associated with a specific section."""
        endpoint = f"sections/{section_id}/rois"
        params = {"skip": skip, "limit": limit}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return [ROIResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []

    async def list_all(
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
        endpoint = "rois"
        params = {
            "specimen_id": specimen_id,
            "block_id": block_id,
            "cutting_session_id": cutting_session_id,
            "section_id": section_id,
            "is_parent_roi": is_parent_roi,
            "skip": skip,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return [ROIResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []

    async def create(self, roi_data: ROICreate) -> ROIResponse:
        """Create a new ROI."""
        response_data = await self._post("rois", data=roi_data.model_dump(exclude_unset=True))
        return ROIResponse.model_validate(response_data)

    async def get(self, roi_id: int) -> ROIResponse:
        """Get a specific ROI by its integer ID."""
        response_data = await self._get(f"rois/{roi_id}")
        return ROIResponse.model_validate(response_data)

    async def update(self, roi_id: int, roi_data: ROIUpdate) -> ROIResponse:
        """Update an existing ROI."""
        update_payload = roi_data.model_dump(exclude_unset=True)
        response_data = await self._patch(f"rois/{roi_id}", data=update_payload)
        return ROIResponse.model_validate(response_data)

    async def delete(self, roi_id: int) -> None:
        """Delete an ROI."""
        await self._delete(f"rois/{roi_id}")

    async def get_children(self, roi_id: int, skip: int = 0, limit: int = 10) -> ROIChildrenResponse:
        """Get child ROIs for a specific parent ROI."""
        endpoint = f"rois/{roi_id}/children"
        params = {"skip": skip, "limit": limit}
        response_data = await self._get(endpoint, params=params)
        return ROIChildrenResponse.model_validate(response_data)
