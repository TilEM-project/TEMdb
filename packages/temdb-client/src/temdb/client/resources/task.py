import builtins
from typing import Any

from temdb.models import (
    AcquisitionResponse,
    AcquisitionTaskCreate,
    AcquisitionTaskResponse,
    AcquisitionTaskUpdate,
)

from .base import BaseResource, kwargs2model


class AcquisitionTaskResource(BaseResource):
    """Resource class for interacting with Acquisition Task endpoints."""

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        specimen_id: str | None = None,
        block_id: str | None = None,
        roi_id: str | None = None,
        kind: str | None = None,
        media_id: str | None = None,
        task_group_id: str | None = None,
        current_only: bool = True,
        skip_destroyed: bool = True,
        skip_completed: bool = True,
        imageable: bool = False,
        loaded_media_ids: builtins.list[str] | None = None,
        **kwargs: Any,
    ) -> builtins.list[AcquisitionTaskResponse]:
        """List acquisition tasks with optional filtering and pagination.

        Work fetch is list(imageable=True, loaded_media_ids=[...]) —
        only tasks the scope can physically image right now are returned.
        """
        params = {
            "skip": skip,
            "limit": limit,
            "specimen_id": specimen_id,
            "block_id": block_id,
            "roi_id": roi_id,
            "kind": kind,
            "media_id": media_id,
            "task_group_id": str(task_group_id) if task_group_id is not None else None,
            "current_only": current_only,
            "skip_destroyed": skip_destroyed,
            "skip_completed": skip_completed,
            "imageable": imageable,
            "loaded_media_id": loaded_media_ids,
        }
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get("acquisition-tasks", params=params)
        return (
            [AcquisitionTaskResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )

    @kwargs2model(AcquisitionTaskCreate)
    async def create(self, task_data: AcquisitionTaskCreate) -> AcquisitionTaskResponse:
        """Create a new acquisition task."""
        response_data = await self._post(
            "acquisition-tasks", data=task_data.model_dump(mode="json", exclude_unset=True)
        )
        return AcquisitionTaskResponse.model_validate(response_data)

    async def get(self, task_id: str) -> AcquisitionTaskResponse:
        """Get a specific acquisition task by ID; its status is derived from runs."""
        response_data = await self._get(f"acquisition-tasks/{task_id}")
        return AcquisitionTaskResponse.model_validate(response_data)

    @kwargs2model(AcquisitionTaskUpdate)
    async def update(self, task_id: str, update_data: AcquisitionTaskUpdate) -> AcquisitionTaskResponse:
        """Update an existing acquisition task."""
        endpoint = f"acquisition-tasks/{task_id}"
        update_payload = update_data.model_dump(mode="json", exclude_unset=True)
        response_data = await self._patch(endpoint, data=update_payload)
        return AcquisitionTaskResponse.model_validate(response_data)

    @kwargs2model(AcquisitionTaskCreate)
    async def supersede(self, task_id: str, new_task: AcquisitionTaskCreate) -> AcquisitionTaskResponse:
        """Replace a task with a corrected plan; the old task is marked superseded."""
        response_data = await self._post(
            f"acquisition-tasks/{task_id}/supersede",
            data=new_task.model_dump(mode="json", exclude_unset=True),
        )
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

    async def create_batch(
        self, tasks_data: builtins.list[AcquisitionTaskCreate], group: bool = False
    ) -> builtins.list[AcquisitionTaskResponse]:
        """Create a batch of acquisition tasks; group=True mints one shared task_group_id."""
        payload = {
            "tasks": [task.model_dump(mode="json", exclude_unset=True) for task in tasks_data],
            "group": group,
        }
        response_data = await self._post("acquisition-tasks/batch", data=payload)
        return (
            [AcquisitionTaskResponse.model_validate(item) for item in response_data]
            if isinstance(response_data, list)
            else []
        )
