from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from temdb.models import (
    AcquisitionTaskCreate,
    AcquisitionTaskStatus,
    AcquisitionTaskUpdate,
)
from temdb.server.database import DatabaseManager
from temdb.server.dependencies import get_db_manager
from temdb.server.documents import (
    AcquisitionDocument as Acquisition,
)
from temdb.server.documents import (
    AcquisitionTaskDocument as AcquisitionTask,
)
from temdb.server.documents import (
    BlockDocument as Block,
)
from temdb.server.documents import (
    ROIDocument as ROI,
)
from temdb.server.documents import (
    SpecimenDocument as Specimen,
)
from temdb.server.responses.task import AcquisitionTaskRead

acquisition_task_api = APIRouter(
    tags=["Acquisition Tasks"],
)


def _to_read(task: AcquisitionTask) -> AcquisitionTaskRead:
    return AcquisitionTaskRead.from_doc(task)


@acquisition_task_api.get(
    "/acquisition-tasks",
    response_model=list[AcquisitionTaskRead],
)
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: AcquisitionTaskStatus | None = None,
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    roi_id: str | None = Query(None, description="Filter by human-readable ROI ID"),
    task_type: str | None = None,
):
    """List acquisition tasks."""
    query: dict = {}
    if status:
        query["status"] = status
    if task_type:
        query["task_type"] = task_type
    if specimen_id:
        query["specimen_id"] = specimen_id
    if block_id:
        query["block_id"] = block_id
    if roi_id:
        query["roi_id"] = roi_id

    tasks = await AcquisitionTask.find(query).skip(skip).limit(limit).to_list()
    return [AcquisitionTaskRead.from_doc(t) for t in tasks]


@acquisition_task_api.post(
    "/acquisition-tasks",
    response_model=AcquisitionTaskRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(task_data: AcquisitionTaskCreate):
    """Create a new acquisition task with sequential operations."""
    try:
        specimen = await Specimen.find_one(Specimen.specimen_id == task_data.specimen_id)
        if not specimen:
            raise HTTPException(404, f"Specimen '{task_data.specimen_id}' not found")

        block = await Block.find_one(
            Block.block_id == task_data.block_id,
            Block.specimen_ref == specimen.id,
        )
        if not block:
            raise HTTPException(
                404,
                f"Block '{task_data.block_id}' not found for specimen '{task_data.specimen_id}'",
            )

        roi = await ROI.find_one(ROI.roi_id == task_data.roi_id)
        if not roi:
            raise HTTPException(404, f"ROI '{task_data.roi_id}' not found")

        if roi.block_id != block.block_id or roi.specimen_id != specimen.specimen_id:
            raise HTTPException(
                400,
                f"ROI '{task_data.roi_id}' does not belong to block '{block.block_id}' "
                f"or specimen '{specimen.specimen_id}'",
            )

        if await AcquisitionTask.find_one({"task_id": task_data.task_id}):
            raise HTTPException(400, f"Task ID '{task_data.task_id}' already exists")

        new_task = AcquisitionTask(
            task_id=task_data.task_id,
            specimen_id=task_data.specimen_id,
            block_id=task_data.block_id,
            roi_id=task_data.roi_id,
            specimen_ref=specimen.id,
            block_ref=block.id,
            roi_ref=roi.id,
            tags=task_data.tags,
            metadata=task_data.metadata,
            task_type=task_data.task_type,
        )

        await new_task.insert()
        return _to_read(new_task)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Failed to create task due to an internal error: {str(e)}")


@acquisition_task_api.get("/acquisition-tasks/{task_id}", response_model=AcquisitionTaskRead)
async def get_task(task_id: str, version: int | None = None):
    query: dict = {"task_id": task_id}
    if version:
        query["version"] = version
    sort_order = [("version", -1)] if not version else None
    task = await AcquisitionTask.find_one(query, sort=sort_order)
    if not task:
        detail = f"Acquisition task ID '{task_id}'" + (f" version {version}" if version else "") + " not found."
        raise HTTPException(status_code=404, detail=detail)
    return _to_read(task)


@acquisition_task_api.patch("/acquisition-tasks/{task_id}", response_model=AcquisitionTaskRead)
async def update_task(task_id: str, updated_fields: AcquisitionTaskUpdate = Body(...)):
    existing_task = await AcquisitionTask.find_one({"task_id": task_id}, sort=[("version", -1)])
    if not existing_task:
        raise HTTPException(404, f"Task ID '{task_id}' not found")
    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(400, "No update fields provided")
    needs_save = False
    for field, value in update_data.items():
        if hasattr(existing_task, field) and getattr(existing_task, field) != value:
            setattr(existing_task, field, value)
            needs_save = True
    if needs_save:
        existing_task.updated_at = datetime.now(timezone.utc)
        await existing_task.save()
    return _to_read(existing_task)


@acquisition_task_api.delete("/acquisition-tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    task = await AcquisitionTask.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(404, f"Task ID '{task_id}' not found")
    acq_count = await Acquisition.find(Acquisition.acquisition_task_ref == task.id).count()
    if acq_count > 0:
        raise HTTPException(400, f"Cannot delete task '{task_id}': {acq_count} acquisitions exist.")
    await task.delete()
    return None


@acquisition_task_api.get(
    "/acquisition-tasks/{task_id}/acquisitions",
    response_model=list,
)
async def get_task_acquisitions(task_id: str, skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    task = await AcquisitionTask.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(404, f"Task ID '{task_id}' not found")
    return (
        await Acquisition.find(Acquisition.acquisition_task_ref == task.id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@acquisition_task_api.post("/acquisition-tasks/{task_id}/status", response_model=AcquisitionTaskRead)
async def update_task_status(task_id: str, status: AcquisitionTaskStatus = Body(..., embed=True)):
    existing_task = await AcquisitionTask.find_one({"task_id": task_id}, sort=[("version", -1)])
    if not existing_task:
        raise HTTPException(404, f"Task ID '{task_id}' not found")
    if existing_task.status == status:
        return _to_read(existing_task)
    existing_task.status = status
    existing_task.updated_at = datetime.now(timezone.utc)
    await existing_task.save()
    return _to_read(existing_task)


@acquisition_task_api.post(
    "/acquisition-tasks/batch",
    response_model=list[AcquisitionTaskRead],
    status_code=status.HTTP_201_CREATED,
)
async def create_tasks_batch(
    tasks: list[AcquisitionTaskCreate],
    db_manager: DatabaseManager = Depends(get_db_manager),
):
    """Create multiple acquisition tasks with sequential validation and creation."""
    created_task_internal_ids = []
    processed_task_ids = set()

    try:
        for task_data in tasks:
            if task_data.task_id in processed_task_ids:
                raise HTTPException(400, f"Duplicate task ID '{task_data.task_id}' in batch.")
            processed_task_ids.add(task_data.task_id)

            if await AcquisitionTask.find_one({"task_id": task_data.task_id}):
                raise HTTPException(400, f"Task ID '{task_data.task_id}' already exists.")

        for task_data in tasks:
            specimen = await Specimen.find_one(Specimen.specimen_id == task_data.specimen_id)
            if not specimen:
                raise HTTPException(
                    404,
                    f"Specimen '{task_data.specimen_id}' not found for task '{task_data.task_id}'",
                )

            block = await Block.find_one(
                Block.block_id == task_data.block_id,
                Block.specimen_ref == specimen.id,
            )
            if not block:
                raise HTTPException(
                    404,
                    f"Block '{task_data.block_id}' not found for task '{task_data.task_id}'",
                )

            roi = await ROI.find_one(ROI.roi_id == task_data.roi_id)
            if not roi:
                raise HTTPException(
                    404,
                    f"ROI '{task_data.roi_id}' not found for task '{task_data.task_id}'",
                )

            if roi.block_id != block.block_id or roi.specimen_id != specimen.specimen_id:
                raise HTTPException(
                    400,
                    f"ROI '{roi.roi_id}' does not match block/specimen for task '{task_data.task_id}'",
                )

            new_task = AcquisitionTask(
                task_id=task_data.task_id,
                specimen_id=task_data.specimen_id,
                block_id=task_data.block_id,
                roi_id=task_data.roi_id,
                specimen_ref=specimen.id,
                block_ref=block.id,
                roi_ref=roi.id,
                tags=task_data.tags,
                metadata=task_data.metadata,
                task_type=task_data.task_type,
            )

            insert_result = await new_task.insert()
            created_task_internal_ids.append(insert_result.id)

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            raise HTTPException(
                500,
                f"Failed to create tasks batch due to an internal error: {str(e)}",
            )
    created_tasks = await AcquisitionTask.find({"_id": {"$in": created_task_internal_ids}}).to_list(length=None)
    if not created_tasks:
        raise HTTPException(500, "Failed to retrieve created tasks after batch insertion.")

    return [AcquisitionTaskRead.from_doc(t) for t in created_tasks]
