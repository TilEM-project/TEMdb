import builtins
from typing import Any

from temdb.models import (
    SectionResponse,
    SubstrateApertures,
    SubstrateCreate,
    SubstrateResponse,
    SubstrateUpdate,
)

from .base import BaseResource, accepts_keywords, without_none


class SubstrateResource(BaseResource):
    """Resource class for interacting with Substrate endpoints."""

    async def list(
        self,
        media_type: str | None = None,
        layout_id: str | None = None,
        available: bool | None = None,
        cursor: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> list[SubstrateResponse]:
        """List substrates with optional filtering and pagination."""
        params = without_none(media_type=media_type, layout_id=layout_id, available=available, **kwargs)
        return await self._list("substrates", SubstrateResponse, params, cursor=cursor, offset=offset, limit=limit)

    @accepts_keywords(SubstrateCreate)
    async def create(self, substrate_data: SubstrateCreate) -> SubstrateResponse:
        """Create a new substrate."""
        response_data = await self._post("substrates", data=substrate_data.model_dump(exclude_unset=True))
        return SubstrateResponse.model_validate(response_data)

    async def get(self, media_id: str) -> SubstrateResponse:
        """Get a specific substrate by ID."""
        response_data = await self._get(f"substrates/{media_id}")
        return SubstrateResponse.model_validate(response_data)

    @accepts_keywords(SubstrateUpdate)
    async def update(self, media_id: str, substrate_data: SubstrateUpdate) -> SubstrateResponse:
        """Update an existing substrate."""
        update_payload = substrate_data.model_dump(exclude_unset=True)
        response_data = await self._patch(f"substrates/{media_id}", data=update_payload)
        return SubstrateResponse.model_validate(response_data)

    async def get_apertures(self, media_id: str) -> SubstrateApertures:
        """Get a substrate's layout with each aperture's shape, status and sections."""
        response_data = await self._get(f"substrates/{media_id}/apertures")
        return SubstrateApertures.model_validate(response_data)

    async def delete(self, media_id: str) -> None:
        """Delete a substrate."""
        await self._delete(f"substrates/{media_id}")

    async def list_related_sections(
        self, media_id: str, cursor: str | None = None, offset: int | None = None, limit: int | None = None
    ) -> builtins.list[SectionResponse]:
        """List sections related to a specific substrate."""
        endpoint = f"substrates/{media_id}/sections"
        return await self._list(endpoint, SectionResponse, {}, cursor=cursor, offset=offset, limit=limit)
