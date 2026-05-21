import builtins
from typing import Any

from temdb.models import (
    AcquisitionResponse,
    AcquisitionTaskCreate,
    AcquisitionTaskResponse,
    AcquisitionTaskStatus,
    AcquisitionTaskUpdate,
)

from ._base import SyncResourceBase


class SyncAcquisitionTaskResourceWrapper(SyncResourceBase):
    """Synchronous wrapper for the AcquisitionTaskResource."""

    def list(
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
        return self._run(
            self._async_resource.list(
                skip=skip,
                limit=limit,
                status=status,
                specimen_id=specimen_id,
                block_id=block_id,
                roi_id=roi_id,
                task_type=task_type,
                **kwargs,
            )
        )

    def create(self, task_data: AcquisitionTaskCreate) -> AcquisitionTaskResponse:
        return self._run(self._async_resource.create(task_data))

    def get(self, task_id: str, version: int | None = None) -> AcquisitionTaskResponse:
        return self._run(self._async_resource.get(task_id, version=version))

    def update(self, task_id: str, update_data: AcquisitionTaskUpdate) -> AcquisitionTaskResponse:
        return self._run(self._async_resource.update(task_id, update_data))

    def delete(self, task_id: str) -> None:
        return self._run(self._async_resource.delete(task_id))

    def list_related_acquisitions(
        self, task_id: str, skip: int = 0, limit: int = 100
    ) -> builtins.list[AcquisitionResponse]:
        return self._run(self._async_resource.list_related_acquisitions(task_id, skip=skip, limit=limit))

    def update_status(self, task_id: str, status: AcquisitionTaskStatus) -> AcquisitionTaskResponse:
        return self._run(self._async_resource.update_status(task_id, status))

    def create_batch(self, tasks_data: builtins.list[AcquisitionTaskCreate]) -> builtins.list[AcquisitionTaskResponse]:
        return self._run(self._async_resource.create_batch(tasks_data))
