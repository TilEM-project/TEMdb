import uuid
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import (
    AcquisitionResponse,
    AcquisitionTaskCreate,
    AcquisitionTaskResponse,
    AcquisitionTaskUpdate,
)
from temdb.server.dependencies import get_async_session
from temdb.server.ids import uuid7
from temdb.server.sqlmodels import (
    AcquisitionSQLModel,
    AcquisitionTaskSQLModel,
    BlockSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SpecimenSQLModel,
)

from ..utils import include_extra, model_dump_with_extra

acquisition_task_api = APIRouter(
    tags=["Acquisition Tasks"],
)


def derive_task_state(runs: list[AcquisitionSQLModel]) -> str:
    """Task state is a function of its runs.

    pending  - no runs
    acquired - runs exist, none qc-resolved yet (includes in-flight runs)
    complete - a run reached qc_pass
    failed   - every run is failed/aborted
    needs_review - newest run is qc_fail/needs_review
    """
    if not runs:
        return "pending"
    if any(r.qc_state == "qc_pass" for r in runs):
        return "complete"
    if all(r.status in ("failed", "aborted") for r in runs):
        return "failed"
    newest = max(runs, key=lambda r: r.start_time)
    if newest.qc_state in ("qc_fail", "needs_review"):
        return "needs_review"
    return "acquired"


def _task_response(task: AcquisitionTaskSQLModel, derived_status: str) -> AcquisitionTaskResponse:
    """Build the response model, filling in the derived (non-column) status field."""
    payload = model_dump_with_extra(
        AcquisitionTaskResponse.model_validate(task),
        mode="json",
        extra_source=task,
    )
    payload["status"] = derived_status
    return AcquisitionTaskResponse.model_validate(payload)


async def _runs_by_task(session: AsyncSession, task_ids: list[str]) -> dict[str, list[AcquisitionSQLModel]]:
    """Fetch all runs for the given tasks, grouped by task_id."""
    grouped: dict[str, list[AcquisitionSQLModel]] = defaultdict(list)
    if not task_ids:
        return grouped
    runs_query = select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_task_id.in_(task_ids))
    runs = (await session.execute(runs_query)).scalars().all()
    for run in runs:
        grouped[run.acquisition_task_id].append(run)
    return grouped


async def _validate_lineage(session: AsyncSession, task_data: AcquisitionTaskCreate) -> tuple:
    """Validate the specimen/block/ROI triple of a task create payload.

    Returns (specimen_ref, block_ref, roi_ref) internal ids; all None for a
    lens_correction task created without lineage.
    """
    if task_data.roi_id is None and task_data.specimen_id is None and task_data.block_id is None:
        return None, None, None
    if not (task_data.roi_id and task_data.specimen_id and task_data.block_id):
        raise HTTPException(422, "specimen_id, block_id, and roi_id must be provided together")
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
    return specimen_obj.id, block_obj.id, roi_obj.id


def _task_from_create(
    task_data: AcquisitionTaskCreate, task_group_id: uuid.UUID | None = None
) -> AcquisitionTaskSQLModel:
    """Build an AcquisitionTaskSQLModel from a validated create payload."""
    return AcquisitionTaskSQLModel(
        task_id=task_data.task_id,
        specimen_id=task_data.specimen_id,
        block_id=task_data.block_id,
        roi_id=task_data.roi_id,
        kind=task_data.kind,
        task_group_id=task_group_id if task_group_id is not None else task_data.task_group_id,
        tilt_angle_deg=task_data.tilt_angle_deg,
        sub_region=task_data.sub_region,
        tags=task_data.tags,
        metadata_json=task_data.metadata,
        created_at=task_data.created_at or datetime.now(timezone.utc),
        extra=task_data.model_extra,
    )


@acquisition_task_api.get("/acquisition-tasks", response_model=list[AcquisitionTaskResponse])
@include_extra
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    roi_id: str | None = Query(None, description="Filter by human-readable ROI ID"),
    kind: str | None = Query(None, description="Filter by task kind (montage, lens_correction)"),
    media_id: str | None = Query(None, description="Filter by media ID (substrate)"),
    task_group_id: uuid.UUID | None = Query(None, description="Filter by task group; results ordered by tilt angle"),
    current_only: bool = Query(True, description="Filter out superseded tasks"),
    skip_destroyed: bool = Query(True, description="Filter out tasks whose ROI section is destroyed"),
    skip_completed: bool = Query(True, description="Filter out tasks with QC-pending or QC-passed runs"),
    imageable: bool = Query(False, description="Only tasks that can be imaged right now"),
    loaded_media_id: list[str] | None = Query(
        None,
        description="Substrates physically loaded in the scope; restricts imageable montage tasks",
    ),
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
    if kind:
        filters.append(AcquisitionTaskSQLModel.kind == kind)
    if specimen_id:
        filters.append(AcquisitionTaskSQLModel.specimen_id == specimen_id)
    if block_id:
        filters.append(AcquisitionTaskSQLModel.block_id == block_id)
    if roi_id:
        filters.append(AcquisitionTaskSQLModel.roi_id == roi_id)
    if media_id:
        filters.append(ROISQLModel.substrate_media_id == media_id)
    if task_group_id is not None:
        filters.append(AcquisitionTaskSQLModel.task_group_id == task_group_id)
        statement = statement.order_by(AcquisitionTaskSQLModel.tilt_angle_deg)
    if current_only or imageable:
        filters.append(AcquisitionTaskSQLModel.superseded_by.is_(None))
    if skip_destroyed or imageable:
        statement = statement.outerjoin(
            SectionSQLModel,
            SectionSQLModel.section_id == ROISQLModel.section_id,
        )
        filters.append(SectionSQLModel.condition.is_distinct_from("destroyed"))
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
    if imageable:
        blocking_run = exists(
            select(AcquisitionSQLModel.id).where(
                AcquisitionSQLModel.acquisition_task_id == AcquisitionTaskSQLModel.task_id,
                or_(
                    AcquisitionSQLModel.end_time.is_(None),
                    and_(
                        AcquisitionSQLModel.status == "complete",
                        AcquisitionSQLModel.qc_state.in_(["pending", "qc_pass", "needs_review"]),
                    ),
                ),
            )
        )
        filters.append(~blocking_run)
        if loaded_media_id:
            filters.append(
                or_(
                    AcquisitionTaskSQLModel.kind == "lens_correction",
                    ROISQLModel.substrate_media_id.in_(loaded_media_id),
                )
            )
    if filters:
        statement = statement.where(and_(*filters))

    rows = (await session.execute(statement.offset(skip).limit(limit))).all()
    if not rows:
        return []
    tasks = [row[0] for row in rows]
    runs_map = await _runs_by_task(session, [task.task_id for task in tasks])
    return [_task_response(task, derive_task_state(runs_map[task.task_id])) for task in tasks]


@acquisition_task_api.post(
    "/acquisition-tasks", status_code=status.HTTP_201_CREATED, response_model=AcquisitionTaskResponse
)
@include_extra
async def create_task(
    task_data: AcquisitionTaskCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new acquisition task (a plan; its state derives from runs)."""
    await _validate_lineage(session, task_data)
    existing = await session.scalars(
        select(AcquisitionTaskSQLModel).where(AcquisitionTaskSQLModel.task_id == task_data.task_id)
    )
    if existing.one_or_none() is not None:
        raise HTTPException(400, f"Task ID '{task_data.task_id}' already exists")
    new_task = _task_from_create(task_data)
    session.add(new_task)
    await session.commit()
    await session.refresh(new_task)
    return _task_response(new_task, derive_task_state([]))


@acquisition_task_api.get("/acquisition-tasks/{task_id}", response_model=AcquisitionTaskResponse)
@include_extra
async def get_task(
    task_id: str,
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
    row = (await session.execute(statement)).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Acquisition task ID '{task_id}' not found.")
    task, _specimen_ref, _block_ref, _roi_ref = row
    runs = (
        (await session.execute(select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_task_id == task_id)))
        .scalars()
        .all()
    )
    return _task_response(task, derive_task_state(list(runs)))


@acquisition_task_api.patch("/acquisition-tasks/{task_id}", response_model=AcquisitionTaskResponse)
@include_extra
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
        )
    ).first()
    if row is None:
        raise HTTPException(404, f"Task ID '{task_id}' not found")
    task_obj, _specimen_ref, _block_ref, _roi_ref = row
    update_data = updated_fields.model_dump(
        mode="json",
        exclude_unset=True,
        extra=False,
    )
    if not update_data:
        raise HTTPException(400, "No update fields provided")
    if "metadata" in update_data:
        task_obj.metadata_json = update_data.pop("metadata")
    for field, value in update_data.items():
        setattr(task_obj, field, value)
    if updated_fields.model_extra:
        task_obj.extra = {**(task_obj.extra or {}), **updated_fields.model_extra}
    task_obj.updated_at = datetime.now(timezone.utc)
    session.add(task_obj)
    await session.commit()
    await session.refresh(task_obj)
    runs = (
        (await session.execute(select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_task_id == task_id)))
        .scalars()
        .all()
    )
    return _task_response(task_obj, derive_task_state(list(runs)))


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


@acquisition_task_api.get("/acquisition-tasks/{task_id}/acquisitions", response_model=list[AcquisitionResponse])
@include_extra
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
    return acquisitions[skip : skip + limit]


@acquisition_task_api.post(
    "/acquisition-tasks/{task_id}/supersede",
    status_code=status.HTTP_201_CREATED,
    response_model=AcquisitionTaskResponse,
)
@include_extra
async def supersede_task(
    task_id: str,
    task_data: AcquisitionTaskCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Replace a task with a corrected plan in a single transaction.

    The old task gets superseded_by = new task_id; existing runs keep pointing
    at the old task_id (uq(task_id) survives — the FK is unaffected).
    """
    old_task = (
        await session.scalars(select(AcquisitionTaskSQLModel).where(AcquisitionTaskSQLModel.task_id == task_id))
    ).one_or_none()
    if old_task is None:
        raise HTTPException(404, f"Task ID '{task_id}' not found")
    if old_task.superseded_by is not None:
        raise HTTPException(409, f"Task '{task_id}' is already superseded by '{old_task.superseded_by}'")
    existing = await session.scalars(
        select(AcquisitionTaskSQLModel).where(AcquisitionTaskSQLModel.task_id == task_data.task_id)
    )
    if existing.one_or_none() is not None:
        raise HTTPException(400, f"Task ID '{task_data.task_id}' already exists")
    await _validate_lineage(session, task_data)
    new_task = _task_from_create(task_data)
    session.add(new_task)
    await session.flush()
    old_task.superseded_by = task_data.task_id
    old_task.updated_at = datetime.now(timezone.utc)
    session.add(old_task)
    await session.commit()
    await session.refresh(new_task)
    return _task_response(new_task, derive_task_state([]))


@acquisition_task_api.post(
    "/acquisition-tasks/batch", status_code=status.HTTP_201_CREATED, response_model=list[AcquisitionTaskResponse]
)
@include_extra
async def create_tasks_batch(
    tasks: list[AcquisitionTaskCreate] = Body(...),
    group: bool = Body(False),
    session: AsyncSession = Depends(get_async_session),
):
    """Create multiple acquisition tasks in a single transaction.

    With group=true the server mints one task_group_id and stamps it on every
    task in the batch (tilt-series contract, spec §13).
    """
    processed_ids: set[str] = set()
    for task_data in tasks:
        if task_data.task_id in processed_ids:
            raise HTTPException(400, f"Duplicate task ID '{task_data.task_id}' in batch.")
        processed_ids.add(task_data.task_id)
        existing = await session.scalars(
            select(AcquisitionTaskSQLModel).where(AcquisitionTaskSQLModel.task_id == task_data.task_id)
        )
        if existing.one_or_none() is not None:
            raise HTTPException(400, f"Task ID '{task_data.task_id}' already exists.")

    group_id = uuid7() if group else None
    new_tasks = []
    for task_data in tasks:
        await _validate_lineage(session, task_data)
        new_task = _task_from_create(task_data, task_group_id=group_id)
        session.add(new_task)
        new_tasks.append(new_task)
    await session.commit()
    for new_task in new_tasks:
        await session.refresh(new_task)
    created_ids = [new_task.id for new_task in new_tasks]

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
        task.id: _task_response(task, derive_task_state([]))
        for task, _specimen_ref, _block_ref, _roi_ref in created_rows
    }
    return [created_map[internal_id] for internal_id in created_ids if internal_id in created_map]
