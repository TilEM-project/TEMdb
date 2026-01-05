from typing import Any

from temdb.models import (
    BlockCreate,
    BlockResponse,
    BlockUpdate,
    CuttingSessionResponse,
)

from .base import BaseResource


class BlockResource(BaseResource):
    """Resource class for interacting with Block endpoints."""

    async def list_by_specimen(
        self, specimen_id: str, skip: int = 0, limit: int = 100, **kwargs: Any
    ) -> list[BlockResponse]:
        """List blocks associated with a specific specimen."""
        endpoint = f"blocks/specimens/{specimen_id}/blocks"
        params = {"skip": skip, "limit": limit}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return [BlockResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []

    async def list_all(
        self,
        specimen_id: str | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[BlockResponse]:
        """List all blocks, optionally filtering by specimen_id."""
        endpoint = "blocks"
        params = {"skip": skip, "limit": limit, "specimen_id": specimen_id}
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return [BlockResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []

    async def create(self, block_data: BlockCreate) -> BlockResponse:
        """Create a new block."""
        response_data = await self._post("blocks", data=block_data.model_dump(exclude_unset=True))
        return BlockResponse.model_validate(response_data)

    async def get(self, specimen_id: str, block_id: str) -> BlockResponse:
        """Get a specific block by specimen and block ID."""
        endpoint = f"blocks/specimens/{specimen_id}/blocks/{block_id}"
        response_data = await self._get(endpoint)
        return BlockResponse.model_validate(response_data)

    async def update(self, specimen_id: str, block_id: str, block_data: BlockUpdate) -> BlockResponse:
        """Update an existing block."""
        endpoint = f"blocks/specimens/{specimen_id}/blocks/{block_id}"
        update_payload = block_data.model_dump(exclude_unset=True)
        response_data = await self._patch(endpoint, data=update_payload)
        return BlockResponse.model_validate(response_data)

    async def delete(self, specimen_id: str, block_id: str) -> None:
        """Delete a block."""
        endpoint = f"blocks/specimens/{specimen_id}/blocks/{block_id}"
        await self._delete(endpoint)

    async def get_cut_sessions(
        self, specimen_id: str, block_id: str, skip: int = 0, limit: int = 100
    ) -> list[CuttingSessionResponse]:
        """Get cutting sessions related to a specific block."""
        endpoint = f"blocks/specimens/{specimen_id}/blocks/{block_id}/cut-sessions"
        params = {"skip": skip, "limit": limit}
        response_data = await self._get(endpoint, params=params)
        return (
            [CuttingSessionResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )
