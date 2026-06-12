from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import (
    AcquisitionTaskCreate,
    AcquisitionTaskStatus,
    AcquisitionTaskUpdate,
)
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import (
    AcquisitionSQLModel,
    AcquisitionTaskSQLModel,
    BlockSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SpecimenSQLModel,
)

acquisition_task_api = APIRouter(
    tags=["Acquisition Tasks"],
)


def _task_payload(
    task: AcquisitionTaskSQLModel,
    specimen_id: int | None = None,
    block_id: int | None = None,
    roi_id: int | None = None,
) -> dict:
    payload = {
        "_id": str(task.id),
        "task_id": task.task_id,
        "specimen_id": task.specimen_id,
        "block_id": task.block_id,
        "roi_id": task.roi_id,
        "task_type": task.task_type,
        "version": task.version,
        "status": task.status,
        "error_message": task.error_message,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "tags": task.tags or [],
        "metadata": task.metadata_json or {},
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
    payload["specimen_ref"] = {"id": str(specimen_id)} if specimen_id is not None else None
    payload["block_ref"] = {"id": str(block_id)} if block_id is not None else None
    payload["roi_ref"] = {"id": str(roi_id)} if roi_id is not None else None
    return payload


@acquisition_task_api.get("/acquisition-tasks")
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    roi_id: str | None = Query(None, description="Filter by human-readable ROI ID"),
    task_type: str | None = None,
    media_id: str | None = Query(None, description="Filter by media ID (substrate)"),
    skip_destroyed: bool = Query(True, description="Filter out tasks whose ROI section is destroyed"),
    skip_completed: bool = Query(True, description="Filter out tasks with QC_PENDING or QC_PASSED acquisitions"),
    session: AsyncSession = Depends(get_async_session),
):
    """List acquisition tasks."""
    statement = (
        select(
            AcquisitionTaskSQLModel,
            SpecimenSQLModel.id,
            BlockSQLModel.id,
            ROISQLModel.id,
        )
        .select_from(AcquisitionTaskSQLModel)
        .outerjoin(
            SpecimenSQLModel,
            SpecimenSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
        )
        .outerjoin(
            BlockSQLModel,
            and_(
                BlockSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
                BlockSQLModel.block_id == AcquisitionTaskSQLModel.block_id,
            ),
        )
        .outerjoin(
            ROISQLModel,
            ROISQLModel.roi_id == AcquisitionTaskSQLModel.roi_id,
        )
    )
    filters = []
    if task_type:
        filters.append(AcquisitionTaskSQLModel.task_type == task_type)
    if specimen_id:
        filters.append(AcquisitionTaskSQLModel.specimen_id == specimen_id)
    if block_id:
        filters.append(AcquisitionTaskSQLModel.block_id == block_id)
    if roi_id:
        filters.append(AcquisitionTaskSQLModel.roi_id == roi_id)
    if media_id:
        filters.append(ROISQLModel.substrate_media_id == media_id)
    if skip_destroyed:
        statement = statement.outerjoin(
            SectionSQLModel,
            SectionSQLModel.section_id == ROISQLModel.section_id,
        )
        filters.append(SectionSQLModel.destroyed.is_not(True))
    if skip_completed:
        completed_subq = (
            select(AcquisitionSQLModel.acquisition_task_id)
            .where(
                AcquisitionSQLModel.status == "complete",
                AcquisitionSQLModel.qc_state.in_(["pending", "qc_pass"]),
            )
            .scalar_subquery()
        )
        filters.append(AcquisitionTaskSQLModel.task_id.not_in(completed_subq))
    if filters:
        statement = statement.where(and_(*filters))

    rows = (await session.execute(statement.offset(skip).limit(limit))).all()
    if not rows:
        return []
    return [_task_payload(task, specimen_ref, block_ref, roi_ref) for task, specimen_ref, block_ref, roi_ref in rows]


@acquisition_task_api.post("/acquisition-tasks", status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: AcquisitionTaskCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new acquisition task with sequential operations."""
    validation_row = (
        await session.execute(
            select(
                SpecimenSQLModel,
                BlockSQLModel,
                ROISQLModel,
            )
            .select_from(SpecimenSQLModel)
            .outerjoin(
                BlockSQLModel,
                and_(
                    BlockSQLModel.specimen_id == SpecimenSQLModel.specimen_id,
                    BlockSQLModel.block_id == task_data.block_id,
                ),
            )
            .outerjoin(ROISQLModel, ROISQLModel.roi_id == task_data.roi_id)
            .where(SpecimenSQLModel.specimen_id == task_data.specimen_id)
        )
    ).first()
    specimen_obj = validation_row[0] if validation_row else None
    if specimen_obj is None:
        raise HTTPException(404, f"Specimen '{task_data.specimen_id}' not found")
    block_obj = validation_row[1]
    if block_obj is None:
        raise HTTPException(404, f"Block '{task_data.block_id}' not found for specimen '{task_data.specimen_id}'")
    roi_obj = validation_row[2]
    if roi_obj is None:
        raise HTTPException(404, f"ROI '{task_data.roi_id}' not found")
    if roi_obj.block_id != block_obj.block_id or roi_obj.specimen_id != specimen_obj.specimen_id:
        raise HTTPException(
            400,
            f"ROI '{task_data.roi_id}' does not belong to block '{block_obj.block_id}' "
            f"or specimen '{specimen_obj.specimen_id}'",
        )
    existing = await session.exec(
        select(AcquisitionTaskSQLModel).where(AcquisitionTaskSQLModel.task_id == task_data.task_id)
    )
    if existing.one_or_none() is not None:
        raise HTTPException(400, f"Task ID '{task_data.task_id}' already exists")
    new_task = AcquisitionTaskSQLModel(
        task_id=task_data.task_id,
        specimen_id=task_data.specimen_id,
        block_id=task_data.block_id,
        roi_id=task_data.roi_id,
        tags=task_data.tags,
        metadata_json=task_data.metadata,
        task_type=task_data.task_type,
        version=task_data.version,
        status=task_data.status.value,
        error_message=task_data.error_message,
        started_at=task_data.started_at,
        completed_at=task_data.completed_at,
        created_at=datetime.now(timezone.utc),
    )
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    return _task_payload(new_task, specimen_obj.id, block_obj.id, roi_obj.id)


@acquisition_task_api.get("/acquisition-tasks/{task_id}")
async def get_task(
    task_id: str,
    version: int | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    statement = (
        select(
            AcquisitionTaskSQLModel,
            SpecimenSQLModel.id,
            BlockSQLModel.id,
            ROISQLModel.id,
        )
        .select_from(AcquisitionTaskSQLModel)
        .outerjoin(
            SpecimenSQLModel,
            SpecimenSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
        )
        .outerjoin(
            BlockSQLModel,
            and_(
                BlockSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
                BlockSQLModel.block_id == AcquisitionTaskSQLModel.block_id,
            ),
        )
        .outerjoin(ROISQLModel, ROISQLModel.roi_id == AcquisitionTaskSQLModel.roi_id)
        .where(AcquisitionTaskSQLModel.task_id == task_id)
    )
    if version is not None:
        statement = statement.where(AcquisitionTaskSQLModel.version == version)
    else:
        statement = statement.order_by(AcquisitionTaskSQLModel.version.desc())
    row = (await session.execute(statement)).first()
    if row is None:
        detail = f"Acquisition task ID '{task_id}'" + (f" version {version}" if version else "") + " not found."
        raise HTTPException(status_code=404, detail=detail)
    task, specimen_ref, block_ref, roi_ref = row
    return _task_payload(task, specimen_ref, block_ref, roi_ref)


@acquisition_task_api.patch("/acquisition-tasks/{task_id}")
async def update_task(
    task_id: str,
    updated_fields: AcquisitionTaskUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    row = (
        await session.execute(
            select(
                AcquisitionTaskSQLModel,
                SpecimenSQLModel.id,
                BlockSQLModel.id,
                ROISQLModel.id,
            )
            .select_from(AcquisitionTaskSQLModel)
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
            )
            .outerjoin(
                BlockSQLModel,
                and_(
                    BlockSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
                    BlockSQLModel.block_id == AcquisitionTaskSQLModel.block_id,
                ),
            )
            .outerjoin(ROISQLModel, ROISQLModel.roi_id == AcquisitionTaskSQLModel.roi_id)
            .where(AcquisitionTaskSQLModel.task_id == task_id)
            .order_by(AcquisitionTaskSQLModel.version.desc())
        )
    ).first()
    if row is None:
        raise HTTPException(404, f"Task ID '{task_id}' not found")
    task_obj, specimen_ref, block_ref, roi_ref = row
    update_data = updated_fields.model_dump(mode="json", exclude_unset=True)
    if not update_data:
        raise HTTPException(400, "No update fields provided")
    changed = False
    for field, value in update_data.items():
        if field == "metadata":
            if task_obj.metadata_json != value:
                task_obj.metadata_json = value
                changed = True
            continue
        if field == "status":
            value = value if isinstance(value, str) else value.value
        if hasattr(task_obj, field) and getattr(task_obj, field) != value:
            setattr(task_obj, field, value)
            changed = True
    if changed:
        task_obj.updated_at = datetime.now(timezone.utc)
        session.add(task_obj)
        await session.commit()
        await session.refresh(task_obj)
    return _task_payload(task_obj, specimen_ref, block_ref, roi_ref)


@acquisition_task_api.delete("/acquisition-tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str, session: AsyncSession = Depends(get_async_session)):
    dependency_row = (
        await session.execute(
            select(AcquisitionTaskSQLModel, AcquisitionSQLModel.id)
            .select_from(AcquisitionTaskSQLModel)
            .outerjoin(
                AcquisitionSQLModel,
                AcquisitionSQLModel.acquisition_task_id == AcquisitionTaskSQLModel.task_id,
            )
            .where(AcquisitionTaskSQLModel.task_id == task_id)
        )
    ).first()
    if dependency_row is None:
        raise HTTPException(404, f"Task ID '{task_id}' not found")
    task_obj, acquisition_id = dependency_row
    if acquisition_id is not None:
        raise HTTPException(400, f"Cannot delete task '{task_id}': acquisitions exist.")
    await session.delete(task_obj)
    await session.commit()
    return None


@acquisition_task_api.get("/acquisition-tasks/{task_id}/acquisitions")
async def get_task_acquisitions(
    task_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    joined_rows = (
        await session.execute(
            select(AcquisitionTaskSQLModel.id, AcquisitionSQLModel)
            .select_from(AcquisitionTaskSQLModel)
            .outerjoin(
                AcquisitionSQLModel,
                AcquisitionSQLModel.acquisition_task_id == AcquisitionTaskSQLModel.task_id,
            )
            .where(AcquisitionTaskSQLModel.task_id == task_id)
        )
    ).all()
    if not joined_rows:
        raise HTTPException(404, f"Task ID '{task_id}' not found")
    acquisitions = [row[1] for row in joined_rows if row[1] is not None]
    return [acq.model_dump() for acq in acquisitions[skip : skip + limit]]


@acquisition_task_api.post("/acquisition-tasks/{task_id}/status")
async def update_task_status(
    task_id: str,
    status: AcquisitionTaskStatus = Body(..., embed=True),
    session: AsyncSession = Depends(get_async_session),
):
    row = (
        await session.execute(
            select(
                AcquisitionTaskSQLModel,
                SpecimenSQLModel.id,
                BlockSQLModel.id,
                ROISQLModel.id,
            )
            .select_from(AcquisitionTaskSQLModel)
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
            )
            .outerjoin(
                BlockSQLModel,
                and_(
                    BlockSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
                    BlockSQLModel.block_id == AcquisitionTaskSQLModel.block_id,
                ),
            )
            .outerjoin(ROISQLModel, ROISQLModel.roi_id == AcquisitionTaskSQLModel.roi_id)
            .where(AcquisitionTaskSQLModel.task_id == task_id)
            .order_by(AcquisitionTaskSQLModel.version.desc())
        )
    ).first()
    if row is None:
        raise HTTPException(404, f"Task ID '{task_id}' not found")

    task_obj, specimen_ref, block_ref, roi_ref = row
    if task_obj.status != status.value:
        task_obj.status = status.value
        task_obj.updated_at = datetime.now(timezone.utc)
        session.add(task_obj)
        await session.commit()
        await session.refresh(task_obj)

    return _task_payload(task_obj, specimen_ref, block_ref, roi_ref)


@acquisition_task_api.post("/acquisition-tasks/batch", status_code=status.HTTP_201_CREATED)
async def create_tasks_batch(
    tasks: list[AcquisitionTaskCreate],
    session: AsyncSession = Depends(get_async_session),
):
    """Create multiple acquisition tasks with sequential validation and creation."""
    processed_ids: set[str] = set()
    created_ids: list[int] = []
    for task_data in tasks:
        if task_data.task_id in processed_ids:
            raise HTTPException(400, f"Duplicate task ID '{task_data.task_id}' in batch.")
        processed_ids.add(task_data.task_id)
        existing = await session.exec(
            select(AcquisitionTaskSQLModel).where(AcquisitionTaskSQLModel.task_id == task_data.task_id)
        )
        if existing.one_or_none() is not None:
            raise HTTPException(400, f"Task ID '{task_data.task_id}' already exists.")

    for task_data in tasks:
        validation_row = (
            await session.execute(
                select(
                    SpecimenSQLModel,
                    BlockSQLModel,
                    ROISQLModel,
                )
                .select_from(SpecimenSQLModel)
                .outerjoin(
                    BlockSQLModel,
                    and_(
                        BlockSQLModel.specimen_id == SpecimenSQLModel.specimen_id,
                        BlockSQLModel.block_id == task_data.block_id,
                    ),
                )
                .outerjoin(ROISQLModel, ROISQLModel.roi_id == task_data.roi_id)
                .where(SpecimenSQLModel.specimen_id == task_data.specimen_id)
            )
        ).first()
        specimen_obj = validation_row[0] if validation_row else None
        if specimen_obj is None:
            raise HTTPException(404, f"Specimen '{task_data.specimen_id}' not found for task '{task_data.task_id}'")
        block_obj = validation_row[1]
        if block_obj is None:
            raise HTTPException(404, f"Block '{task_data.block_id}' not found for task '{task_data.task_id}'")
        roi_obj = validation_row[2]
        if roi_obj is None:
            raise HTTPException(404, f"ROI '{task_data.roi_id}' not found for task '{task_data.task_id}'")
        if roi_obj.block_id != block_obj.block_id or roi_obj.specimen_id != specimen_obj.specimen_id:
            raise HTTPException(
                400,
                f"ROI '{roi_obj.roi_id}' does not match block/specimen for task '{task_data.task_id}'",
            )
        new_task = AcquisitionTaskSQLModel(
            task_id=task_data.task_id,
            specimen_id=task_data.specimen_id,
            block_id=task_data.block_id,
            roi_id=task_data.roi_id,
            task_type=task_data.task_type,
            version=task_data.version,
            status=task_data.status.value,
            tags=task_data.tags,
            metadata_json=task_data.metadata,
            created_at=datetime.now(timezone.utc),
        )
        session.add(new_task)
        await session.commit()  # preserve partial-success semantics
        await session.refresh(new_task)
        created_ids.append(new_task.id)

    created_rows = (
        await session.execute(
            select(
                AcquisitionTaskSQLModel,
                SpecimenSQLModel.id,
                BlockSQLModel.id,
                ROISQLModel.id,
            )
            .select_from(AcquisitionTaskSQLModel)
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
            )
            .outerjoin(
                BlockSQLModel,
                and_(
                    BlockSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
                    BlockSQLModel.block_id == AcquisitionTaskSQLModel.block_id,
                ),
            )
            .outerjoin(ROISQLModel, ROISQLModel.roi_id == AcquisitionTaskSQLModel.roi_id)
            .where(AcquisitionTaskSQLModel.id.in_(created_ids))
        )
    ).all()
    created_map = {
        task.id: _task_payload(task, specimen_ref, block_ref, roi_ref)
        for task, specimen_ref, block_ref, roi_ref in created_rows
    }
    return [created_map[task_id] for task_id in created_ids if task_id in created_map]
