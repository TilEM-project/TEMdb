import builtins
from typing import Any

from temdb.models import (
    SubstrateLayoutCreate,
    SubstrateLayoutResponse,
    SubstrateLayoutUpdate,
    SubstrateResponse,
)

from .base import BaseResource


class SubstrateLayoutResource(BaseResource):
    """Resource class for interacting with Substrate Layout endpoints."""

    async def list(
        self,
        media_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[SubstrateLayoutResponse]:
        """List substrate layouts with optional filtering and pagination."""
        params = {
            "media_type": media_type,
            "skip": skip,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get("layouts", params=params)
        return (
            [SubstrateLayoutResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )

    async def create(self, layout_data: SubstrateLayoutCreate) -> SubstrateLayoutResponse:
        """Create a new substrate layout."""
        response_data = await self._post("layouts", data=layout_data.model_dump(exclude_unset=True))
        return SubstrateLayoutResponse.model_validate(response_data)

    async def get(self, layout_id: str) -> SubstrateLayoutResponse:
        """Get a specific substrate layout by ID."""
        response_data = await self._get(f"layouts/{layout_id}")
        return SubstrateLayoutResponse.model_validate(response_data)

    async def update(self, layout_id: str, layout_data: SubstrateLayoutUpdate) -> SubstrateLayoutResponse:
        """Update an existing substrate layout."""
        update_payload = layout_data.model_dump(exclude_unset=True)
        response_data = await self._patch(f"layouts/{layout_id}", data=update_payload)
        return SubstrateLayoutResponse.model_validate(response_data)

    async def delete(self, layout_id: str) -> None:
        """Delete a substrate layout."""
        await self._delete(f"layouts/{layout_id}")

    async def list_related_substrates(
        self, layout_id: str, skip: int = 0, limit: int = 100
    ) -> builtins.list[SubstrateResponse]:
        """List substrates of a given layout."""
        endpoint = f"layouts/{layout_id}/substrates"
        params = {"skip": skip, "limit": limit}
        response_data = await self._get(endpoint, params=params)
        return (
            [SubstrateResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )
