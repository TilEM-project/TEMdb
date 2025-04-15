from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from temdb.models.v2.acquisition import Acquisition
from temdb.models.v2.task import (
    AcquisitionTask,
    AcquisitionTaskCreate,
    AcquisitionTaskStatus,
    AcquisitionTaskUpdate,
)

acquisition_task_api = APIRouter(
    tags=["Acquisition Tasks"],
)


@acquisition_task_api.get("/acquisition-tasks", response_model=List[AcquisitionTask])
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[AcquisitionTaskStatus] = None,
    specimen_id: Optional[str] = None,
    block_id: Optional[str] = None,
    task_type: Optional[str] = None,
):
    """List acquisition tasks with optional filtering"""

    filters = {}
    if status:
        filters["status"] = status
    if specimen_id:
        filters["specimen_id"] = specimen_id
    if block_id:
        filters["block_id"] = block_id
    if task_type:
        filters["task_type"] = task_type

    return await AcquisitionTask.find(filters).skip(skip).limit(limit).to_list()


@acquisition_task_api.post("/acquisition-tasks", response_model=AcquisitionTask)
async def create_task(task: AcquisitionTaskCreate):
    """Create a new acquisition task"""

    existing_task = await AcquisitionTask.find_one({"task_id": task.task_id})
    if existing_task:
        raise HTTPException(status_code=400, detail="Task ID already exists")

    new_task = AcquisitionTask(**task.model_dump())
    await new_task.insert()
    return new_task


@acquisition_task_api.get(
    "/acquisition-tasks/{task_id}", response_model=AcquisitionTask
)
async def get_task(task_id: str, version: Optional[int] = None):
    """Get a specific acquisition task, optionally a specific version"""
    if version:
        task = await AcquisitionTask.find_one({"task_id": task_id, "version": version})
    else:
        task = await AcquisitionTask.find_one({"task_id": task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Acquisition task not found")

    return task


@acquisition_task_api.patch(
    "/acquisition-tasks/{task_id}", response_model=AcquisitionTask
)
async def update_task(task_id: str, updated_fields: AcquisitionTaskUpdate = Body(...)):
    """Update an acquisition task"""
    existing_task = await AcquisitionTask.find_one({"task_id": task_id})
    if not existing_task:
        raise HTTPException(status_code=404, detail="Acquisition task not found")

    update_data = updated_fields.model_dump(exclude_unset=True)

    if update_data:

        for field, value in update_data.items():
            setattr(existing_task, field, value)

        existing_task.updated_at = datetime.now(timezone.utc)
        await existing_task.save()

    return existing_task


@acquisition_task_api.delete("/acquisition-tasks/{task_id}", response_model=dict)
async def delete_task(task_id: str):
    """Delete an acquisition task"""
    task = await AcquisitionTask.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Acquisition task not found")

    related_acquisitions = await Acquisition.find(
        {"acquisition_task_id": task_id}
    ).count()

    if related_acquisitions > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete task with {related_acquisitions} related acquisitions",
        )

    await task.delete()

    return {"message": "Acquisition task deleted successfully"}


@acquisition_task_api.get(
    "/acquisition-tasks/{task_id}/acquisitions", response_model=List[Acquisition]
)
async def get_task_acquisitions(
    task_id: str, skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    """Get acquisitions related to a specific task"""
    task = await AcquisitionTask.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Acquisition task not found")

    acquisitions = (
        await Acquisition.find({"acquisition_task_id": task_id})
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    return acquisitions


@acquisition_task_api.post(
    "/acquisition-tasks/{task_id}/status", response_model=AcquisitionTask
)
async def update_task_status(
    task_id: str, status: AcquisitionTaskStatus = Body(..., embed=True)
):
    """Update only the status of an acquisition task (convenience endpoint)"""
    existing_task = await AcquisitionTask.find_one({"task_id": task_id})
    if not existing_task:
        raise HTTPException(status_code=404, detail="Acquisition task not found")

    new_version = existing_task.version + 1
    new_task = AcquisitionTask(
        **existing_task.model_dump(),
        version=new_version,
        status=status,
        updated_at=datetime.now(timezone.utc),
    )
    await new_task.insert()

    return new_task


@acquisition_task_api.post(
    "/acquisition-tasks/batch", response_model=List[AcquisitionTask]
)
async def create_tasks_batch(tasks: List[AcquisitionTaskCreate]):
    """Create multiple acquisition tasks at once"""

    new_tasks = []
    for task in tasks:
        existing_task = await AcquisitionTask.find_one({"task_id": task.task_id})
        if existing_task:
            raise HTTPException(
                status_code=400, detail=f"Task ID {task.task_id} already exists"
            )

        new_task = AcquisitionTask(**task.model_dump())
        new_tasks.append(new_task)

        AcquisitionTask.insert_many(new_tasks)
    return new_tasks
