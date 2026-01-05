import builtins
from typing import Any

from temdb.models import (
    SectionResponse,
    SubstrateCreate,
    SubstrateResponse,
    SubstrateUpdate,
)

from .base import BaseResource


class SubstrateResource(BaseResource):
    """Resource class for interacting with Substrate endpoints."""

    async def list(
        self,
        media_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[SubstrateResponse]:
        """List substrates with optional filtering and pagination."""
        params = {
            "media_type": media_type,
            "status": status,
            "skip": skip,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get("substrates", params=params)
        return (
            [SubstrateResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )

    async def create(self, substrate_data: SubstrateCreate) -> SubstrateResponse:
        """Create a new substrate."""
        response_data = await self._post("substrates", data=substrate_data.model_dump(exclude_unset=True))
        return SubstrateResponse.model_validate(response_data)

    async def get(self, media_id: str) -> SubstrateResponse:
        """Get a specific substrate by ID."""
        response_data = await self._get(f"substrates/{media_id}")
        return SubstrateResponse.model_validate(response_data)

    async def update(self, media_id: str, substrate_data: SubstrateUpdate) -> SubstrateResponse:
        """Update an existing substrate."""
        update_payload = substrate_data.model_dump(exclude_unset=True)
        response_data = await self._patch(f"substrates/{media_id}", data=update_payload)
        return SubstrateResponse.model_validate(response_data)

    async def delete(self, media_id: str) -> None:
        """Delete a substrate."""
        await self._delete(f"substrates/{media_id}")

    async def list_related_sections(
        self, media_id: str, skip: int = 0, limit: int = 100
    ) -> builtins.list[SectionResponse]:
        """List sections related to a specific substrate."""
        endpoint = f"substrates/{media_id}/sections"
        params = {"skip": skip, "limit": limit}
        response_data = await self._get(endpoint, params=params)
        return (
            [SectionResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []
        )
