import builtins
from typing import Any

from temdb.models import (
    AcquisitionResponse,
    AcquisitionTaskCreate,
    AcquisitionTaskResponse,
    AcquisitionTaskStatus,
    AcquisitionTaskUpdate,
)

from .base import BaseResource


class AcquisitionTaskResource(BaseResource):
    """Resource class for interacting with Acquisition Task endpoints."""

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        status: AcquisitionTaskStatus | None = None,
        specimen_id: str | None = None,
        block_id: str | None = None,
        roi_id: int | None = None,
        task_type: str | None = None,
        **kwargs: Any,
    ) -> list[AcquisitionTaskResponse]:
        """List acquisition tasks with optional filtering and pagination."""
        params = {
            "skip": skip,
            "limit": limit,
            "status": status.value if status else None,
            "specimen_id": specimen_id,
            "block_id": block_id,
            "roi_id": roi_id,
            "task_type": task_type,
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get("acquisition-tasks", params=params)
        return (
            [AcquisitionTaskResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )

    async def create(self, task_data: AcquisitionTaskCreate) -> AcquisitionTaskResponse:
        """Create a new acquisition task."""
        response_data = await self._post("acquisition-tasks", data=task_data.model_dump(exclude_unset=True))
        return AcquisitionTaskResponse.model_validate(response_data)

    async def get(self, task_id: str, version: int | None = None) -> AcquisitionTaskResponse:
        """Get a specific acquisition task by ID, optionally a specific version."""
        endpoint = f"acquisition-tasks/{task_id}"
        params = {}
        if version is not None:
            params["version"] = version
        response_data = await self._get(endpoint, params=params if params else None)
        return AcquisitionTaskResponse.model_validate(response_data)

    async def update(self, task_id: str, update_data: AcquisitionTaskUpdate) -> AcquisitionTaskResponse:
        """Update an existing acquisition task."""
        endpoint = f"acquisition-tasks/{task_id}"
        update_payload = update_data.model_dump(exclude_unset=True)
        response_data = await self._patch(endpoint, data=update_payload)
        return AcquisitionTaskResponse.model_validate(response_data)

    async def delete(self, task_id: str) -> None:
        """Delete an acquisition task."""
        endpoint = f"acquisition-tasks/{task_id}"
        await self._delete(endpoint)

    async def list_related_acquisitions(
        self, task_id: str, skip: int = 0, limit: int = 100
    ) -> builtins.list[AcquisitionResponse]:
        """List acquisitions related to a specific acquisition task."""
        endpoint = f"acquisition-tasks/{task_id}/acquisitions"
        params = {"skip": skip, "limit": limit}
        response_data = await self._get(endpoint, params=params)
        return (
            [AcquisitionResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )

    async def update_status(self, task_id: str, status: AcquisitionTaskStatus) -> AcquisitionTaskResponse:
        """Update the status of an acquisition task."""
        endpoint = f"acquisition-tasks/{task_id}/status"
        status_payload = {"status": status.value}
        response_data = await self._post(endpoint, data=status_payload)
        return AcquisitionTaskResponse.model_validate(response_data)

    async def create_batch(
        self, tasks_data: builtins.list[AcquisitionTaskCreate]
    ) -> builtins.list[AcquisitionTaskResponse]:
        """Create a batch of acquisition tasks."""
        payload = [task.model_dump(exclude_unset=True) for task in tasks_data]
        response_data = await self._post("acquisition-tasks/batch", data=payload)
        return (
            [AcquisitionTaskResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )
