import asyncio
import builtins
from typing import Any

from temdb.models import (
    AcquisitionResponse,
    AcquisitionTaskCreate,
    AcquisitionTaskResponse,
    AcquisitionTaskUpdate,
)

from ..task import AcquisitionTaskResource


class SyncAcquisitionTaskResourceWrapper:
    """Synchronous wrapper for the AcquisitionTaskResource."""

    def __init__(self, async_resource: AcquisitionTaskResource):
        self._async_resource = async_resource

    def list(
        self,
        skip: int = 0,
        limit: int = 100,
        specimen_id: str | None = None,
        block_id: str | None = None,
        roi_id: int | None = None,
        task_type: str | None = None,
        skip_destroyed: bool = True,
        skip_completed: bool = True,
        **kwargs: Any,
    ) -> list[AcquisitionTaskResponse]:
        """List acquisition tasks."""
        return asyncio.run(
            self._async_resource.list(
                skip=skip,
                limit=limit,
                specimen_id=specimen_id,
                block_id=block_id,
                roi_id=roi_id,
                task_type=task_type,
                skip_destroyed=skip_destroyed,
                skip_completed=skip_completed,
                **kwargs,
            )
        )

    def create(self, task_data: AcquisitionTaskCreate) -> AcquisitionTaskResponse:
        """Create a new acquisition task."""
        return asyncio.run(self._async_resource.create(task_data))

    def get(self, task_id: str, version: int | None = None) -> AcquisitionTaskResponse:
        """Get a specific acquisition task by ID."""
        return asyncio.run(self._async_resource.get(task_id, version=version))

    def update(self, task_id: str, update_data: AcquisitionTaskUpdate) -> AcquisitionTaskResponse:
        """Update an existing acquisition task."""
        return asyncio.run(self._async_resource.update(task_id, update_data))

    def delete(self, task_id: str) -> None:
        """Delete an acquisition task."""
        return asyncio.run(self._async_resource.delete(task_id))

    def list_related_acquisitions(
        self, task_id: str, skip: int = 0, limit: int = 100
    ) -> builtins.list[AcquisitionResponse]:
        """List acquisitions related to a specific task."""
        return asyncio.run(self._async_resource.list_related_acquisitions(task_id, skip=skip, limit=limit))

    def create_batch(self, tasks_data: builtins.list[AcquisitionTaskCreate]) -> builtins.list[AcquisitionTaskResponse]:
        """Create a batch of acquisition tasks."""
        return asyncio.run(self._async_resource.create_batch(tasks_data))
