from typing import Any

from temdb.models import (
    CuttingSessionCreate,
    CuttingSessionResponse,
    CuttingSessionUpdate,
    SectionResponse,
)

from .base import BaseResource


class CuttingSessionResource(BaseResource):
    """Resource class for interacting with Cutting Session endpoints."""

    async def list_by_block(
        self,
        specimen_id: str,
        block_id: str,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[CuttingSessionResponse]:
        """List cutting sessions associated with a specific block."""
        endpoint = f"cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions"
        params = {"skip": skip, "limit": limit}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return (
            [CuttingSessionResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )

    async def list_all(
        self,
        specimen_id: str | None = None,
        block_id: str | None = None,
        operator: str | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[CuttingSessionResponse]:
        """List all cutting sessions, optionally filtering."""
        endpoint = "cutting-sessions"
        params = {
            "skip": skip,
            "limit": limit,
            "specimen_id": specimen_id,
            "block_id": block_id,
            "operator": operator,
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get(endpoint, params=params)
        return (
            [CuttingSessionResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )

    async def create(self, session_data: CuttingSessionCreate) -> CuttingSessionResponse:
        """Create a new cutting session."""
        response_data = await self._post(
            "cutting-sessions",
            data=session_data.model_dump(mode="json", exclude_unset=True),
        )
        return CuttingSessionResponse.model_validate(response_data)

    async def get(self, specimen_id: str, block_id: str, cutting_session_id: str) -> CuttingSessionResponse:
        """Get a specific cutting session by specimen, block, and session ID."""
        endpoint = f"cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions/{cutting_session_id}"
        response_data = await self._get(endpoint)
        return CuttingSessionResponse.model_validate(response_data)

    async def update(self, cutting_session_id: str, session_data: CuttingSessionUpdate) -> CuttingSessionResponse:
        """Update an existing cutting session."""
        endpoint = f"cutting-sessions/{cutting_session_id}"
        update_payload = session_data.model_dump(exclude_unset=True)
        response_data = await self._patch(endpoint, data=update_payload)
        return CuttingSessionResponse.model_validate(response_data)

    async def delete(self, cutting_session_id: str) -> None:
        """Delete a cutting session."""
        endpoint = f"cutting-sessions/{cutting_session_id}"
        await self._delete(endpoint)

    async def list_sections(
        self,
        specimen_id: str,
        block_id: str,
        cutting_session_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SectionResponse]:
        """List sections associated with a specific cutting session."""
        endpoint = f"cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions/{cutting_session_id}/sections"
        params = {"skip": skip, "limit": limit}
        response_data = await self._get(endpoint, params=params)
        return (
            [SectionResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []
        )
