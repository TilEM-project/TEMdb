import asyncio
from typing import Any

from temdb.models import (
    CuttingSessionCreate,
    CuttingSessionResponse,
    CuttingSessionUpdate,
    SectionResponse,
)

from ..cutting_session import CuttingSessionResource


class SyncCuttingSessionResourceWrapper:
    """Synchronous wrapper for the CuttingSessionResource."""

    def __init__(self, async_resource: CuttingSessionResource):
        self._async_resource = async_resource

    def list_by_block(
        self,
        specimen_id: str,
        block_id: str,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[CuttingSessionResponse]:
        """List cutting sessions associated with a specific block."""
        return asyncio.run(self._async_resource.list_by_block(specimen_id, block_id, skip=skip, limit=limit, **kwargs))

    def list_all(
        self,
        specimen_id: str | None = None,
        block_id: str | None = None,
        operator: str | None = None,
        skip: int = 0,
        limit: int = 100,
        **kwargs: Any,
    ) -> list[CuttingSessionResponse]:
        """List all cutting sessions, optionally filtering."""
        return asyncio.run(
            self._async_resource.list_all(
                specimen_id=specimen_id,
                block_id=block_id,
                operator=operator,
                skip=skip,
                limit=limit,
                **kwargs,
            )
        )

    def create(self, session_data: CuttingSessionCreate) -> CuttingSessionResponse:
        """Create a new cutting session."""
        return asyncio.run(self._async_resource.create(session_data))

    def get(self, specimen_id: str, block_id: str, cutting_session_id: str) -> CuttingSessionResponse:
        """Get a specific cutting session by specimen, block, and session ID."""
        return asyncio.run(self._async_resource.get(specimen_id, block_id, cutting_session_id))

    def update(self, cutting_session_id: str, session_data: CuttingSessionUpdate) -> CuttingSessionResponse:
        """Update an existing cutting session."""
        return asyncio.run(self._async_resource.update(cutting_session_id, session_data))

    def delete(self, cutting_session_id: str) -> None:
        """Delete a cutting session."""
        return asyncio.run(self._async_resource.delete(cutting_session_id))

    def list_sections(
        self,
        specimen_id: str,
        block_id: str,
        cutting_session_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[SectionResponse]:
        """List sections associated with a specific cutting session."""
        return asyncio.run(
            self._async_resource.list_sections(specimen_id, block_id, cutting_session_id, skip=skip, limit=limit)
        )
