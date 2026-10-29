import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy import SmallInteger, and_, bindparam, delete, func, or_, select, true, tuple_, update
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import (
    RUN_STATUSES,
    AcquisitionCreate,
    AcquisitionFullMetadata,
    AcquisitionResponse,
    AcquisitionUpdate,
    FileObject,
    FileObjectRequest,
    FileObjectResponse,
    TileBulkDeleteResult,
    TileCreate,
    TileDeleteAllResult,
    TileResponse,
    TileUpdate,
)
from temdb.server.config import config
from temdb.server.dependencies import get_async_session, get_storage_client_manager
from temdb.server.sqlmodels import (
    AcquisitionSQLModel,
    AcquisitionTaskSQLModel,
    BlockSQLModel,
    CuttingSessionSQLModel,
    DatasetSQLModel,
    LensCorrectionSQLModel,
    MicroscopeSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SpecimenSQLModel,
    SubstrateSQLModel,
    TileSQLModel,
)
from temdb.server.sqlmodels.tile import format_tile_id, parse_tile_id
from temdb.server.sqlmodels.tile_partition import ensure_tile_partition
from temdb.server.storage import StorageClientManager

from ..utils import drop_null_keys, merge_extra

acquisition_api = APIRouter(
    tags=["Acquisitions"],
)

logger = logging.getLogger(__name__)


def _status_condition(acq_status: str):
    """Axis-1 filter; the literal 'in_flight' selects runs without a terminal status."""
    if acq_status == "in_flight":
        return AcquisitionSQLModel.status.is_(None)
    if acq_status in RUN_STATUSES:
        return AcquisitionSQLModel.status == acq_status
    raise HTTPException(422, f"status filter must be 'in_flight' or one of {RUN_STATUSES}")


def _tile_payload(tile: TileSQLModel, acq_obj: AcquisitionSQLModel) -> dict[str, Any]:
    return {
        "tile_id": format_tile_id(acq_obj.montage_id, tile.row, tile.col, tile.retake),
        "dataset_id": str(tile.dataset_id),
        "acquisition_id": acq_obj.acquisition_id,
        "raster_index": tile.raster_index,
        "stage_position": {"x": tile.stage_x_nm, "y": tile.stage_y_nm, "z": tile.stage_z_nm},
        "raster_position": {"row": tile.row, "col": tile.col},
        "retake": tile.retake,
        "focus_score": tile.focus_score,
        "min_value": tile.min_value,
        "max_value": tile.max_value,
        "mean_value": tile.mean_value,
        "std_value": tile.std_value,
        "image": tile.image,
        "matcher": tile.matcher,
        "supertile_id": tile.supertile_id,
        "supertile_raster_position": tile.supertile_raster_position,
        "created_at": tile.created_at,
        "updated_at": tile.updated_at,
        "acquisition_ref": {"id": str(acq_obj.id)},
    }


def _column_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value.value if hasattr(value, "value") else value


def _has_non_finite(value: Any) -> bool:
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(_has_non_finite(item) for item in value.values())
    if isinstance(value, list):
        return any(_has_non_finite(item) for item in value)
    return False


def _tile_sql_kwargs(tile_data: TileCreate, dataset_id: uuid.UUID, run_id: uuid.UUID) -> dict[str, Any]:
    """Translate the dict-shaped wire model into flattened tile columns."""
    if _has_non_finite(tile_data.model_dump()):
        raise HTTPException(422, f"Tile {tile_data.raster_index} has a NaN or infinite value")
    return {
        "dataset_id": dataset_id,
        "run_id": run_id,
        "row": tile_data.raster_position.row,
        "col": tile_data.raster_position.col,
        "retake": tile_data.retake,
        "raster_index": tile_data.raster_index,
        "stage_x_nm": tile_data.stage_position.x,
        "stage_y_nm": tile_data.stage_position.y,
        "stage_z_nm": tile_data.stage_position.z,
        "focus_score": tile_data.focus_score,
        "min_value": tile_data.min_value,
        "max_value": tile_data.max_value,
        "mean_value": tile_data.mean_value,
        "std_value": tile_data.std_value,
        "image": tile_data.image.model_dump() if tile_data.image else None,
        "matcher": [m.model_dump() for m in tile_data.matcher] if tile_data.matcher else None,
        "supertile_id": tile_data.supertile_id,
        "supertile_raster_position": (
            tile_data.supertile_raster_position.model_dump() if tile_data.supertile_raster_position else None
        ),
    }


async def acquisition_page(
    session: AsyncSession, statement, conditions: list, sort_by: str, sort_order: int, cursor: int | None, limit: int
) -> tuple[list, int, str | None]:
    """Return one page of the statement's rows, the number of acquisitions matching the conditions, and the next cursor.

    Rows are ordered by the sort column and then by id. The cursor is the id of the last acquisition on the previous
    page, and the next cursor is None on the last page.
    """
    total_count = await session.scalar(select(func.count()).select_from(AcquisitionSQLModel).where(*conditions))
    keys = (getattr(AcquisitionSQLModel, sort_by), AcquisitionSQLModel.id)
    ascending = sort_order == 1
    if cursor is not None:
        last = (await session.execute(select(*keys).where(AcquisitionSQLModel.id == cursor))).first()
        if last is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"cursor {cursor} is not an acquisition")
        statement = statement.where(tuple_(*keys) > tuple(last) if ascending else tuple_(*keys) < tuple(last))
    order = [key.asc() if ascending else key.desc() for key in keys]
    rows = (await session.execute(statement.where(*conditions).order_by(*order).limit(limit + 1))).all()
    next_cursor = str(rows[limit - 1][0].id) if len(rows) > limit else None
    return rows[:limit], total_count, next_cursor


@acquisition_api.get("/acquisitions", response_model=dict[str, Any])
async def list_acquisitions(
    response: Response,
    cursor: int | None = Query(None, description="next_cursor of the previous page"),
    limit: int = Query(50, ge=1, le=1000),
    sort_by: Literal["start_time", "acquisition_id"] = Query("start_time", description="Field to sort by"),
    sort_order: int = Query(-1, description="Sort order (-1=desc, 1=asc)"),
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    roi_id: str | None = Query(None, description="Filter by human-readable ROI ID"),
    acquisition_task_id: str | None = Query(None, description="Filter by human-readable Acquisition Task ID"),
    montage_set_name: str | None = Query(None),
    magnification: int | None = Query(None, ge=1),
    acq_status: str | None = Query(
        None,
        alias="status",
        description="Terminal status (complete, aborted, failed) or the literal 'in_flight'",
    ),
    qc_state: str | None = Query(None, description="Filter by QC axis state"),
    kind: str | None = Query(None, description="Filter by run kind (montage, lens_correction)"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    param_tile_focus_lt: float | None = Query(
        None,
        description="Filter acquisitions where the avg_focus_score rollup is less than this value",
    ),
    param_tile_match_quality_lt: float | None = Query(
        None,
        description="Filter acquisitions where tile match quality is less than this value",
    ),
    param_tile_dx_gt: float | None = Query(
        None, description="Filter acquisitions where tile dx is greater than this value"
    ),
    param_tile_dy_gt: float | None = Query(
        None, description="Filter acquisitions where tile dy is greater than this value"
    ),
    fields: list[str] | None = Query(None, description="Fields to return (e.g., ['acquisition_id', 'status'])"),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Retrieve a list of acquisitions with filtering, sorting, and pagination.

    Rollup filters (avg_focus_score) read columns written by ingest/QC services — out of repo.
    """
    conditions = []
    if specimen_id:
        conditions.append(AcquisitionSQLModel.specimen_id == specimen_id)
    if roi_id:
        conditions.append(AcquisitionSQLModel.roi_id == roi_id)
    if acquisition_task_id:
        conditions.append(AcquisitionSQLModel.acquisition_task_id == acquisition_task_id)
    if montage_set_name:
        conditions.append(AcquisitionSQLModel.montage_set_name == montage_set_name)
    if acq_status:
        conditions.append(_status_condition(acq_status))
    if qc_state:
        conditions.append(AcquisitionSQLModel.qc_state == qc_state)
    if kind:
        conditions.append(AcquisitionSQLModel.kind == kind)
    if start_date:
        conditions.append(AcquisitionSQLModel.start_time >= start_date)
    if end_date:
        conditions.append(AcquisitionSQLModel.start_time <= end_date)
    if magnification is not None:
        conditions.append(AcquisitionSQLModel.acquisition_settings.contains({"magnification": magnification}))
    if param_tile_focus_lt is not None:
        conditions.append(AcquisitionSQLModel.avg_focus_score < param_tile_focus_lt)

    if param_tile_match_quality_lt is not None:
        logger.warning(
            "API parameter 'param_tile_match_quality_lt' (%s) is accepted but not yet implemented.",
            param_tile_match_quality_lt,
        )
    if param_tile_dx_gt is not None:
        logger.warning(
            "API parameter 'param_tile_dx_gt' (%s) is accepted but not yet implemented.",
            param_tile_dx_gt,
        )
    if param_tile_dy_gt is not None:
        logger.warning(
            "API parameter 'param_tile_dy_gt' (%s) is accepted but not yet implemented.",
            param_tile_dy_gt,
        )

    rows, total_count, next_cursor = await acquisition_page(
        session, select(AcquisitionSQLModel), conditions, sort_by, sort_order, cursor, limit
    )
    payloads = []
    for (acq,) in rows:
        payload = AcquisitionResponse.model_validate(acq).model_dump(mode="json")
        if fields:
            kept = {field: payload.get(field) for field in fields}
            kept["id"] = payload["id"]
            payload = kept
        payloads.append(payload)
    metadata = {
        "total_count": total_count,
        "returned_count": len(payloads),
        "limit": limit,
        "sort_by": sort_by,
        "sort_order": sort_order if sort_order in [-1, 1] else -1,
        "next_cursor": next_cursor,
    }
    response.headers["Cache-Control"] = "private, max-age=300"
    response.headers["X-Total-Count"] = str(total_count)
    return {"acquisitions": payloads, "metadata": metadata}


@acquisition_api.post("/acquisitions", response_model=AcquisitionResponse, status_code=status.HTTP_201_CREATED)
async def create_acquisition(
    acq_data: AcquisitionCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new acquisition with validation but without transactions.

    Runs start in flight (status NULL, end_time NULL); the terminal status is written
    once via PATCH. Montage runs require ROI/specimen lineage; lens_correction runs
    are exempt and reference their correction via lc_id (never via calibration_info).
    """
    if acq_data.kind == "montage" and acq_data.roi_id is None:
        raise HTTPException(
            422,
            "roi_id is required for kind='montage' acquisitions; only lens_correction runs may omit lineage.",
        )
    existing = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acq_data.acquisition_id)
    )
    if existing.first() is not None:
        raise HTTPException(409, f"Acquisition ID '{acq_data.acquisition_id}' already exists.")
    microscope = await session.scalars(
        select(MicroscopeSQLModel).where(MicroscopeSQLModel.microscope_id == acq_data.microscope_id)
    )
    if microscope.first() is None:
        raise HTTPException(404, f"Microscope '{acq_data.microscope_id}' not found.")
    if acq_data.lc_id is not None:
        lens_correction = await session.scalars(
            select(LensCorrectionSQLModel).where(LensCorrectionSQLModel.lc_id == acq_data.lc_id)
        )
        if lens_correction.first() is None:
            raise HTTPException(404, f"Lens correction '{acq_data.lc_id}' not found.")
    task_row = (
        await session.execute(
            select(AcquisitionTaskSQLModel, SpecimenSQLModel.id)
            .select_from(AcquisitionTaskSQLModel)
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
            )
            .where(AcquisitionTaskSQLModel.task_id == acq_data.acquisition_task_id)
        )
    ).first()
    if task_row is None:
        raise HTTPException(404, f"Acquisition Task '{acq_data.acquisition_task_id}' not found.")
    task_obj, _specimen_ref = task_row
    roi_obj = None
    if acq_data.roi_id is not None:
        roi = await session.scalars(select(ROISQLModel).where(ROISQLModel.roi_id == acq_data.roi_id))
        roi_obj = roi.first()
        if roi_obj is None:
            raise HTTPException(404, f"ROI '{acq_data.roi_id}' not found.")
        if task_obj.roi_id != roi_obj.roi_id:
            raise HTTPException(
                400,
                f"ROI ID '{roi_obj.roi_id}' does not match ROI reference in Task '{task_obj.task_id}'.",
            )
    if acq_data.kind == "montage" and task_obj.specimen_id is None:
        raise HTTPException(
            422,
            f"Task '{task_obj.task_id}' has no specimen lineage; kind='montage' acquisitions require it.",
        )
    replacement_id = None
    if acq_data.replaces_acquisition_id:
        replacement = await session.scalars(
            select(AcquisitionSQLModel).where(
                AcquisitionSQLModel.acquisition_id == str(acq_data.replaces_acquisition_id)
            )
        )
        replacement_obj = replacement.first()
        if replacement_obj is None:
            raise HTTPException(
                404,
                f"Acquisition to replace ID '{acq_data.replaces_acquisition_id}' not found.",
            )
        replacement_id = replacement_obj.acquisition_id
    dataset_uuid = None
    if acq_data.dataset_id is not None:
        try:
            dataset_uuid = uuid.UUID(acq_data.dataset_id)
        except ValueError:
            raise HTTPException(400, f"Invalid dataset_id '{acq_data.dataset_id}'")
    acquisition = AcquisitionSQLModel(
        acquisition_id=acq_data.acquisition_id,
        montage_id=acq_data.montage_id,
        specimen_id=task_obj.specimen_id if roi_obj is not None else None,
        roi_id=roi_obj.roi_id if roi_obj is not None else None,
        acquisition_task_id=task_obj.task_id,
        microscope_id=acq_data.microscope_id,
        dataset_id=dataset_uuid,
        kind=acq_data.kind,
        lc_id=acq_data.lc_id,
        hardware_settings=acq_data.hardware_settings.model_dump(),
        acquisition_settings=acq_data.acquisition_settings.model_dump(),
        calibration_info=acq_data.calibration_info.model_dump() if acq_data.calibration_info else None,
        tilt_angle_deg=acq_data.tilt_angle_deg,
        created_at=acq_data.created_at or datetime.now(timezone.utc),
        start_time=acq_data.start_time or datetime.now(timezone.utc),
        storage_locations=(
            [loc.model_dump(mode="json") for loc in acq_data.storage_locations] if acq_data.storage_locations else None
        ),
        montage_set_name=acq_data.montage_set_name,
        sub_region=acq_data.sub_region.model_dump(mode="json") if acq_data.sub_region else None,
        replaces_acquisition_id=replacement_id,
        extra=drop_null_keys(acq_data.extra),
    )
    session.add(acquisition)
    await session.commit()
    await session.refresh(acquisition)
    return acquisition


@acquisition_api.get("/acquisitions/{acquisition_id}", response_model=AcquisitionResponse)
async def get_acquisition(
    acquisition_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a specific acquisition by its human-readable ID."""
    row = (
        await session.execute(
            select(
                AcquisitionSQLModel,
                SpecimenSQLModel.id,
                ROISQLModel.id,
                AcquisitionTaskSQLModel.id,
            )
            .select_from(AcquisitionSQLModel)
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == AcquisitionSQLModel.specimen_id,
            )
            .outerjoin(
                ROISQLModel,
                ROISQLModel.roi_id == AcquisitionSQLModel.roi_id,
            )
            .outerjoin(
                AcquisitionTaskSQLModel,
                AcquisitionTaskSQLModel.task_id == AcquisitionSQLModel.acquisition_task_id,
            )
            .where(AcquisitionSQLModel.acquisition_id == acquisition_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found")
    acq_obj, _specimen_ref, _roi_ref, _task_ref = row
    return acq_obj


@acquisition_api.patch("/acquisitions/{acquisition_id}", response_model=AcquisitionResponse)
async def update_acquisition(
    acquisition_id: str,
    updated_fields: AcquisitionUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific acquisition."""
    row = (
        await session.execute(
            select(
                AcquisitionSQLModel,
                SpecimenSQLModel.id,
                ROISQLModel.id,
                AcquisitionTaskSQLModel.id,
            )
            .select_from(AcquisitionSQLModel)
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == AcquisitionSQLModel.specimen_id,
            )
            .outerjoin(
                ROISQLModel,
                ROISQLModel.roi_id == AcquisitionSQLModel.roi_id,
            )
            .outerjoin(
                AcquisitionTaskSQLModel,
                AcquisitionTaskSQLModel.task_id == AcquisitionSQLModel.acquisition_task_id,
            )
            .where(AcquisitionSQLModel.acquisition_id == acquisition_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found")
    acq_obj, _specimen_ref, _roi_ref, _task_ref = row
    update_data = updated_fields.model_dump(
        exclude_unset=True,
    )
    if not update_data:
        raise HTTPException(400, "No update data provided")
    extra_changes = update_data.pop("extra", None)
    updated_by = update_data.pop("updated_by", None)
    now = datetime.now(timezone.utc)
    if "end_time" in update_data and "status" not in update_data:
        raise HTTPException(422, "end_time can only be set together with a terminal status")
    if "qc_state" in update_data:
        update_data["qc_state_updated_at"] = now
        update_data["qc_state_updated_by"] = updated_by
    if "transfer_state" in update_data:
        update_data["transfer_state_updated_at"] = now
        update_data["transfer_state_updated_by"] = updated_by
    if "status" in update_data:
        # Terminal status is write-once: compare-and-swap on status IS NULL so a
        # concurrent terminal PATCH cannot rewrite the first writer's result.
        if update_data.get("end_time") is None:
            update_data["end_time"] = now
        values = {
            field: _column_value(value) for field, value in update_data.items() if hasattr(AcquisitionSQLModel, field)
        }
        if extra_changes is not None:
            values["extra"] = merge_extra(AcquisitionSQLModel.extra, extra_changes)
        result = await session.execute(
            update(AcquisitionSQLModel)
            .where(
                AcquisitionSQLModel.acquisition_id == acquisition_id,
                AcquisitionSQLModel.status.is_(None),
            )
            .values(**values)
        )
        if result.rowcount == 0:
            await session.rollback()
            current = (
                await session.execute(
                    select(AcquisitionSQLModel.status).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
                )
            ).first()
            if current is None:
                raise HTTPException(status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found")
            raise HTTPException(
                409,
                f"Acquisition '{acquisition_id}' already has terminal status '{current[0]}'.",
            )
        await session.commit()
        await session.refresh(acq_obj)
        return acq_obj
    for field, value in update_data.items():
        if hasattr(acq_obj, field):
            setattr(acq_obj, field, _column_value(value))
    if extra_changes is not None:
        acq_obj.extra = merge_extra(AcquisitionSQLModel.extra, extra_changes)
    session.add(acq_obj)
    await session.commit()
    await session.refresh(acq_obj)
    return acq_obj


@acquisition_api.delete("/acquisitions/{acquisition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_acquisition(
    acquisition_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a specific acquisition."""
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id).with_for_update()
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found")
    await session.delete(acq_obj)
    await session.commit()
    return None


async def _ensure_dataset_accepts_tiles(session: AsyncSession, dataset_id: uuid.UUID) -> None:
    status = await session.scalar(select(DatasetSQLModel.status).where(DatasetSQLModel.dataset_id == dataset_id))
    if status == "archived":
        raise HTTPException(status_code=409, detail=f"Dataset '{dataset_id}' is archived; it accepts no tiles")
    has_children = (
        await session.scalars(
            select(DatasetSQLModel.dataset_id).where(DatasetSQLModel.parent_dataset_id == dataset_id).limit(1)
        )
    ).first()
    if has_children is not None:
        raise HTTPException(status_code=400, detail="parent datasets hold no tiles")


@acquisition_api.post(
    "/acquisitions/{acquisition_id}/tiles",
    response_model=dict[str, Any],
    status_code=status.HTTP_201_CREATED,
)
async def add_tile_to_acquisition(
    acquisition_id: str,
    tile_data: TileCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Add a single tile to an acquisition."""
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found")
    if acq_obj.dataset_id is None:
        raise HTTPException(
            status_code=409, detail=f"Acquisition '{acquisition_id}' has no dataset_id; cannot store tiles"
        )
    await _ensure_dataset_accepts_tiles(session, acq_obj.dataset_id)
    await ensure_tile_partition(session, acq_obj.dataset_id)
    # Creating a partition locks acquisitions against writes (through the tiles foreign key) until commit.
    await session.commit()
    stmt = (
        pg_insert(TileSQLModel)
        .values(_tile_sql_kwargs(tile_data, acq_obj.dataset_id, acq_obj.run_id))
        .on_conflict_do_nothing(index_elements=list(TileSQLModel.__table__.primary_key))
        .returning(TileSQLModel)
    )
    tile = (await session.execute(stmt)).scalars().first()
    if tile is None:
        tile_id = format_tile_id(
            acq_obj.montage_id, tile_data.raster_position.row, tile_data.raster_position.col, tile_data.retake
        )
        raise HTTPException(409, f"Tile '{tile_id}' already exists in acquisition '{acquisition_id}'")
    payload = _tile_payload(tile, acq_obj)
    await session.commit()
    return payload


@acquisition_api.post("/acquisitions/{acquisition_id}/tiles/bulk", response_model=dict)
async def add_tiles_to_acquisition(
    acquisition_id: str,
    tiles: list[TileCreate],
    session: AsyncSession = Depends(get_async_session),
):
    """Add multiple tiles to an acquisition."""
    row = (
        await session.execute(
            select(
                AcquisitionSQLModel,
                SpecimenSQLModel.id,
                ROISQLModel.id,
                AcquisitionTaskSQLModel.id,
            )
            .select_from(AcquisitionSQLModel)
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == AcquisitionSQLModel.specimen_id,
            )
            .outerjoin(
                ROISQLModel,
                ROISQLModel.roi_id == AcquisitionSQLModel.roi_id,
            )
            .outerjoin(
                AcquisitionTaskSQLModel,
                AcquisitionTaskSQLModel.task_id == AcquisitionSQLModel.acquisition_task_id,
            )
            .where(AcquisitionSQLModel.acquisition_id == acquisition_id)
        )
    ).first()
    if row is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    acq_obj, specimen_ref, roi_ref, task_ref = row
    if acq_obj.dataset_id is None:
        raise HTTPException(409, f"Acquisition '{acquisition_id}' has no dataset_id; cannot store tiles")
    keys = [(tile.raster_position.row, tile.raster_position.col, tile.retake) for tile in tiles]
    repeated = sorted({key for key in keys if keys.count(key) > 1})
    if repeated:
        raise HTTPException(422, f"Tiles (row, col, retake) {repeated} appear more than once in the request")
    await _ensure_dataset_accepts_tiles(session, acq_obj.dataset_id)
    await ensure_tile_partition(session, acq_obj.dataset_id)
    # Creating a partition locks acquisitions against writes (through the tiles foreign key) until commit.
    await session.commit()
    total_tiles = len(tiles)
    inserted = 0
    if tiles:
        # Retried batches are expected (at-least-once ingest): ON CONFLICT DO
        # NOTHING keeps the write-once rows and reports duplicates as skipped.
        rows = [_tile_sql_kwargs(tile, acq_obj.dataset_id, acq_obj.run_id) for tile in tiles]
        columns = TileSQLModel.__table__.c
        # One bound array per column: one value per cell exceeds asyncpg's 32,767-argument limit at 1,928 tiles.
        # dimensions=1 keeps each matcher list as one jsonb element.
        incoming = select(
            *(
                func.unnest(
                    bindparam(key, [row[key] for row in rows], type_=ARRAY(columns[key].type, dimensions=1))
                ).label(key)
                for key in rows[0]
            )
        ).subquery("incoming")
        result = await session.execute(
            pg_insert(TileSQLModel)
            .from_select(list(rows[0]), select(incoming))
            .on_conflict_do_nothing(index_elements=list(TileSQLModel.__table__.primary_key))
        )
        inserted = result.rowcount
        if inserted < total_tiles:
            # Each incoming tile looks up its stored tile by key. OFFSET 0 stops Postgres flattening the LATERAL
            # subquery into a join, whose plan can scan the whole run once per incoming tile.
            stored = (
                select(TileSQLModel)
                .where(
                    TileSQLModel.dataset_id == acq_obj.dataset_id,
                    TileSQLModel.run_id == acq_obj.run_id,
                    TileSQLModel.row == incoming.c.row,
                    TileSQLModel.col == incoming.c.col,
                    TileSQLModel.retake == incoming.c.retake,
                )
                .offset(0)
                .lateral("stored")
            )
            differing = (
                await session.execute(
                    select(stored.c.row, stored.c.col, stored.c.retake)
                    .select_from(incoming)
                    .join(stored, true())
                    .where(or_(*(stored.c[key].is_distinct_from(incoming.c[key]) for key in rows[0])))
                    .order_by(stored.c.row, stored.c.col, stored.c.retake)
                )
            ).all()
            if differing:
                tile_ids = [format_tile_id(acq_obj.montage_id, *key) for key in differing]
                await session.rollback()
                raise HTTPException(409, f"Tiles {tile_ids} are already stored with different values")
        await session.commit()
    return {
        "acquisition_id": acquisition_id,
        "total_received": total_tiles,
        "inserted": inserted,
        "skipped_existing": total_tiles - inserted,
    }


@acquisition_api.get("/acquisitions/{acquisition_id}/tiles", response_model=dict[str, Any])
async def get_tiles_from_acquisition(
    acquisition_id: str,
    cursor: str | None = Query(None, description="next_cursor of the previous page, as 'row,col,retake'"),
    limit: int = Query(100, ge=1, le=1000),
    fields: list[str] | None = Query(None),
    x_min: float | None = Query(
        None, allow_inf_nan=False, description="The min X axis stage coordinate value in nanometers"
    ),
    x_max: float | None = Query(
        None, allow_inf_nan=False, description="The max X axis stage coordinate value in nanometers"
    ),
    y_min: float | None = Query(
        None, allow_inf_nan=False, description="The min Y axis stage coordinate value in nanometers"
    ),
    y_max: float | None = Query(
        None, allow_inf_nan=False, description="The max Y axis stage coordinate value in nanometers"
    ),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve an acquisition's tiles, every retake included, in (row, col, retake) order."""
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    if x_min is not None and x_max is not None and x_min > x_max:
        raise HTTPException(422, "Invalid bounding box: x_min must be <= x_max")
    if y_min is not None and y_max is not None and y_min > y_max:
        raise HTTPException(422, "Invalid bounding box: y_min must be <= y_max")
    after = None
    if cursor is not None:
        try:
            after = tuple(int(part) for part in cursor.split(","))
        except ValueError:
            after = ()
        if len(after) != 3:
            raise HTTPException(422, f"cursor must be 'row,col,retake', got '{cursor}'")
    if acq_obj.dataset_id is None:
        rows = []
    else:
        bbox = []
        if x_min is not None:
            bbox.append(TileSQLModel.stage_x_nm >= x_min)
        if x_max is not None:
            bbox.append(TileSQLModel.stage_x_nm <= x_max)
        if y_min is not None:
            bbox.append(TileSQLModel.stage_y_nm >= y_min)
        if y_max is not None:
            bbox.append(TileSQLModel.stage_y_nm <= y_max)
        query = select(TileSQLModel).where(
            TileSQLModel.dataset_id == acq_obj.dataset_id,
            TileSQLModel.run_id == acq_obj.run_id,
            *bbox,
        )
        key = (TileSQLModel.row, TileSQLModel.col, TileSQLModel.retake)
        if after is not None:
            query = query.where(tuple_(*key) > tuple_(*after))
        query = query.order_by(*key).limit(limit + 1)
        rows = (await session.scalars(query)).all()
    has_more = len(rows) > limit
    tiles = rows[:limit]
    payloads = [_tile_payload(tile, acq_obj) for tile in tiles]
    if fields:
        trimmed = []
        for payload in payloads:
            entry = {field: payload.get(field) for field in fields}
            entry["tile_id"] = payload["tile_id"]
            trimmed.append(entry)
        payloads = trimmed
    next_cursor = f"{tiles[-1].row},{tiles[-1].col},{tiles[-1].retake}" if tiles else None
    return {
        "tiles": payloads,
        "metadata": {
            "returned_count": len(payloads),
            "limit": limit,
            "current_cursor": cursor,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


def _where_tile(acq_obj: AcquisitionSQLModel, tile_id: str) -> list:
    """SQL conditions for one tile of the acquisition; 404 if it has no such tile.

    tile_id is `{montage_id}_r{row:03d}_c{col:03d}`, with `_a{retake}` for a retake, e.g. `{montage_id}_r003_c012_a1`.
    """
    key = parse_tile_id(acq_obj.montage_id, tile_id)
    if key is None:
        raise HTTPException(404, f"Tile ID '{tile_id}' not found in acquisition '{acq_obj.acquisition_id}'")
    row, col, retake = key
    return [
        TileSQLModel.dataset_id == acq_obj.dataset_id,
        TileSQLModel.run_id == acq_obj.run_id,
        TileSQLModel.row == row,
        TileSQLModel.col == col,
        TileSQLModel.retake == retake,
    ]


def _where_tiles(acq_obj: AcquisitionSQLModel, tile_ids: list[str]) -> list:
    """SQL conditions for the listed tiles of the acquisition; a tile_id that is not one of its tiles matches nothing.

    The keys are bound as three arrays: an IN (...) list binds one argument per tile, and asyncpg allows 32,767.
    """
    keys = [key for key in (parse_tile_id(acq_obj.montage_id, tile_id) for tile_id in tile_ids) if key is not None]
    rows, cols, retakes = (list(part) for part in zip(*keys)) if keys else ([], [], [])
    key_rows = select(
        *(
            func.unnest(bindparam(label, values, type_=ARRAY(SmallInteger)))
            for label, values in (("rows", rows), ("cols", cols), ("retakes", retakes))
        )
    )
    return [
        TileSQLModel.dataset_id == acq_obj.dataset_id,
        TileSQLModel.run_id == acq_obj.run_id,
        tuple_(TileSQLModel.row, TileSQLModel.col, TileSQLModel.retake).in_(key_rows),
    ]


@acquisition_api.post("/acquisitions/{acquisition_id}/tiles/images", response_model=dict[str, Any])
async def image_put_urls(
    acquisition_id: str,
    expiration: int | None = Query(3600, description="Expiration time in seconds for the presigned URL"),
    cursor: str | None = Query(None, description="next_cursor of the previous page, as 'row,col,retake'"),
    limit: int = Query(100, ge=1, le=1000),
    tile_ids: list[str] | None = Body(None),
    session: AsyncSession = Depends(get_async_session),
    storage_client_manager: StorageClientManager = Depends(get_storage_client_manager),
):
    """Generate presigned PUT URLs for tiles in an acquisition.

    The tile_id list is optional; if omitted, all tiles in the acquisition are returned.
    """
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.one_or_none()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    tile_query = select(TileSQLModel).where(
        TileSQLModel.dataset_id == acq_obj.dataset_id,
        TileSQLModel.run_id == acq_obj.run_id,
        TileSQLModel.image.isnot(None),
    )
    after = None
    if cursor is not None:
        try:
            after = tuple(int(part) for part in cursor.split(","))
        except ValueError:
            after = ()
        if len(after) != 3:
            raise HTTPException(422, f"cursor must be 'row,col,retake', got '{cursor}'")
    if tile_ids is not None:
        tile_query = tile_query.where(*_where_tiles(acq_obj, tile_ids))
    key = (TileSQLModel.row, TileSQLModel.col, TileSQLModel.retake)
    if after is not None:
        tile_query = tile_query.where(tuple_(*key) > tuple_(*after))
    tile_query = tile_query.order_by(*key).limit(limit + 1)
    tiles = await session.scalars(tile_query)
    tiles_obj = tiles.all()
    has_more = len(tiles_obj) > limit
    tiles_obj = tiles_obj[:limit]
    if not tiles_obj:
        raise HTTPException(404, f"No tiles found for acquisition '{acquisition_id}'")
    urls = {}
    errors = {}
    for tile in tiles_obj:
        if tile.image is None:
            continue
        tile_id = format_tile_id(acq_obj.montage_id, tile.row, tile.col, tile.retake)
        storage_location = FileObjectRequest.from_file_object(tile.image)
        storage_location.expiration = expiration
        storage_client_manager.finalize(storage_location)
        try:
            url_data = storage_client_manager.put_url(storage_location)
            urls[tile_id] = url_data
        except HTTPException as e:
            logger.error(f"Error generating presigned URL for tile {tile_id}: {e.detail}")
            errors[tile_id] = e.detail
    next_cursor = f"{tiles_obj[-1].row},{tiles_obj[-1].col},{tiles_obj[-1].retake}" if tiles_obj else None
    return {
        "urls": urls,
        "metadata": {
            "returned_count": len(urls),
            "limit": limit,
            "current_cursor": cursor,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "errors": errors,
        },
    }


@acquisition_api.get("/acquisitions/{acquisition_id}/tiles/images", response_model=dict[str, Any])
async def image_get_urls(
    acquisition_id: str,
    expiration: int | None = Query(3600, description="Expiration time in seconds for the presigned URL"),
    cursor: str | None = Query(None, description="next_cursor of the previous page, as 'row,col,retake'"),
    limit: int = Query(100, ge=1, le=1000),
    tile_ids: list[str] | None = Body(None),
    session: AsyncSession = Depends(get_async_session),
    storage_client_manager: StorageClientManager = Depends(get_storage_client_manager),
):
    """Generate presigned PUT URLs for tiles in an acquisition.

    The tile_id list is optional; if omitted, all tiles in the acquisition are returned.
    """
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.one_or_none()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    after = None
    if cursor is not None:
        try:
            after = tuple(int(part) for part in cursor.split(","))
        except ValueError:
            after = ()
        if len(after) != 3:
            raise HTTPException(422, f"cursor must be 'row,col,retake', got '{cursor}'")
    tile_query = select(TileSQLModel).where(
        TileSQLModel.dataset_id == acq_obj.dataset_id,
        TileSQLModel.run_id == acq_obj.run_id,
        TileSQLModel.image.isnot(None),
    )
    if tile_ids is not None:
        tile_query = tile_query.where(*_where_tiles(acq_obj, tile_ids))
    key = (TileSQLModel.row, TileSQLModel.col, TileSQLModel.retake)
    if after is not None:
        tile_query = tile_query.where(tuple_(*key) > tuple_(*after))
    tile_query = tile_query.order_by(*key).limit(limit + 1)
    tiles = await session.scalars(tile_query)
    tiles_obj = tiles.all()
    has_more = len(tiles_obj) > limit
    tiles_obj = tiles_obj[:limit]
    if not tiles_obj:
        raise HTTPException(404, f"No tiles found for acquisition '{acquisition_id}'")
    urls = {}
    errors = {}
    for tile in tiles_obj:
        if tile.image is None:
            continue
        tile_id = format_tile_id(acq_obj.montage_id, tile.row, tile.col, tile.retake)
        storage_location = FileObject.model_validate(tile.image)
        try:
            url_data = storage_client_manager.get_url(storage_location, expiration)
            urls[tile_id] = url_data
        except HTTPException as e:
            logger.error(f"Error generating presigned URL for tile {tile_id}: {e.detail}")
            errors[tile_id] = e.detail
    next_cursor = f"{tiles_obj[-1].row},{tiles_obj[-1].col},{tiles_obj[-1].retake}" if tiles_obj else None
    return {
        "urls": urls,
        "metadata": {
            "returned_count": len(urls),
            "limit": limit,
            "current_cursor": cursor,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "errors": errors,
        },
    }


@acquisition_api.delete("/acquisitions/{acquisition_id}/tiles/images", response_model=dict[str, Any])
async def delete_tile_images(
    acquisition_id: str,
    tile_ids: list[str] | None = Body(None),
    cursor: str | None = Query(None, description="next_cursor of the previous page, as 'row,col,retake'"),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_async_session),
    storage_client_manager: StorageClientManager = Depends(get_storage_client_manager),
):
    """Delete the images associated with specific tiles in an acquisition.

    The tile_id list is optional; if omitted, all tiles in the acquisition are deleted.
    """
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.one_or_none()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    after = None
    if cursor is not None:
        try:
            after = tuple(int(part) for part in cursor.split(","))
        except ValueError:
            after = ()
        if len(after) != 3:
            raise HTTPException(422, f"cursor must be 'row,col,retake', got '{cursor}'")
    tile_query = select(TileSQLModel).where(
        TileSQLModel.dataset_id == acq_obj.dataset_id,
        TileSQLModel.run_id == acq_obj.run_id,
        TileSQLModel.image.isnot(None),
    )
    if tile_ids is not None:
        tile_query = tile_query.where(*_where_tiles(acq_obj, tile_ids))
    key = (TileSQLModel.row, TileSQLModel.col, TileSQLModel.retake)
    if after is not None:
        tile_query = tile_query.where(tuple_(*key) > tuple_(*after))
    tile_query = tile_query.order_by(*key).limit(limit + 1)
    tiles = await session.scalars(tile_query)
    tiles_obj = tiles.all()
    has_more = len(tiles_obj) > limit
    tiles_obj = tiles_obj[:limit]
    if not tiles_obj:
        raise HTTPException(404, f"No tile images to delete for acquisition '{acquisition_id}'")
    deleted_tiles = []
    errors = {}
    for tile in tiles_obj:
        if tile.image is None:
            continue
        tile_id = format_tile_id(acq_obj.montage_id, tile.row, tile.col, tile.retake)
        storage_location = FileObject.model_validate(tile.image)
        try:
            storage_client_manager.delete(storage_location)
            tile.image = None
            tile.updated_at = datetime.now(timezone.utc)
            session.add(tile)
            deleted_tiles.append(tile_id)
        except HTTPException as e:
            logger.error(f"Error deleting image for tile {tile_id}: {e.detail}")
            errors[tile_id] = e.detail
    await session.commit()
    next_cursor = f"{tiles_obj[-1].row},{tiles_obj[-1].col},{tiles_obj[-1].retake}" if tiles_obj else None
    return {
        "deleted_images": deleted_tiles,
        "metadata": {
            "returned_count": len(deleted_tiles),
            "limit": limit,
            "current_cursor": cursor,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "errors": errors,
        },
    }


@acquisition_api.get("/acquisitions/{acquisition_id}/tiles/{tile_id}", response_model=TileResponse)
async def get_tile_from_acquisition(
    acquisition_id: str,
    tile_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve one tile of an acquisition by its tile_id."""
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    tile = await session.scalars(select(TileSQLModel).where(*_where_tile(acq_obj, tile_id)))
    tile_obj = tile.first()
    if tile_obj is None:
        raise HTTPException(404, f"Tile ID '{tile_id}' not found in acquisition '{acquisition_id}'")
    return _tile_payload(tile_obj, acq_obj)


@acquisition_api.post("/acquisitions/{acquisition_id}/tiles/{tile_id}/image", response_model=FileObjectResponse)
async def image_put_url(
    acquisition_id: str,
    tile_id: str,
    storage_location: FileObjectRequest | None = Body(None, description="Storage location for the tile image"),
    session: AsyncSession = Depends(get_async_session),
    storage_client_manager: StorageClientManager = Depends(get_storage_client_manager),
):
    """Generate a presigned PUT URL for a tile in an acquisition.

    The storage_location is optional; if omitted, the existing location is used.
    """
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.one_or_none()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    tile = await session.scalars(select(TileSQLModel).where(*_where_tile(acq_obj, tile_id)))
    tile_obj = tile.one_or_none()
    if tile_obj is None:
        raise HTTPException(404, f"Tile ID '{tile_id}' not found in acquisition '{acquisition_id}'")
    if storage_location is None and tile_obj.image is None:
        raise HTTPException(400, "No storage location provided and tile has no existing image")
    if storage_location is None:
        storage_location = FileObjectRequest.from_file_object(tile_obj.image)
    if not storage_location.complete:
        dataset = (
            await session.scalars(select(DatasetSQLModel).where(DatasetSQLModel.dataset_id == acq_obj.dataset_id))
        ).one_or_none()
        if dataset is None:
            raise HTTPException(404, "Could not find dataset for tile")
        if dataset.default_storage is not None:
            storage_location = storage_location.apply_defaults(dataset.default_storage)

    if not storage_location.complete and config.default_storage is not None:
        storage_location = storage_location.apply_defaults(config.default_storage)

    storage_location = storage_client_manager.finalize(storage_location)

    if tile_obj.image is not None and storage_location != tile_obj.image:
        raise HTTPException(400, "Delete the existing image for the tile before uploading a new one.")

    response = storage_client_manager.put_url(storage_location)

    if storage_location != tile_obj.image:
        tile_obj.image = response.dump_file_object()
        tile_obj.updated_at = datetime.now(timezone.utc)
        session.add(tile_obj)
        await session.commit()

    return response


@acquisition_api.get("/acquisitions/{acquisition_id}/tiles/{tile_id}/image", response_model=FileObjectResponse)
async def image_get_url(
    acquisition_id: str,
    tile_id: str,
    expiration: int | None = Query(3600, description="Expiration time in seconds for the presigned URL"),
    session: AsyncSession = Depends(get_async_session),
    storage_client_manager: StorageClientManager = Depends(get_storage_client_manager),
):
    """Generate a presigned GET URL for a tile in an acquisition."""
    tile = TileResponse.model_validate(await get_tile_from_acquisition(acquisition_id, tile_id, session))
    if tile.image is None:
        raise HTTPException(404, f"Tile ID '{tile_id}' has no image")
    return storage_client_manager.get_url(FileObject.model_validate(tile.image), expiration)


@acquisition_api.delete("/acquisitions/{acquisition_id}/tiles/{tile_id}/image", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tile_image(
    acquisition_id: str,
    tile_id: str,
    session: AsyncSession = Depends(get_async_session),
    storage_client_manager: StorageClientManager = Depends(get_storage_client_manager),
):
    """Delete the image associated with a specific tile in an acquisition."""
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.one_or_none()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    tile = await session.scalars(select(TileSQLModel).where(*_where_tile(acq_obj, tile_id)))
    tile_obj = tile.one_or_none()
    if tile_obj is None:
        raise HTTPException(404, f"Tile ID '{tile_id}' not found in acquisition '{acquisition_id}'")
    if tile_obj.image is None:
        raise HTTPException(404, f"Tile ID '{tile_id}' has no image to delete")

    storage_location = FileObject.model_validate(tile_obj.image)

    storage_client_manager.delete(storage_location)

    tile_obj.image = None
    tile_obj.updated_at = datetime.now(timezone.utc)
    session.add(tile_obj)
    await session.commit()


@acquisition_api.get("/acquisitions/{acquisition_id}/tile-count", response_model=dict[str, int])
async def get_tile_count(
    acquisition_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get the number of positions imaged in an acquisition; retakes of a position count once."""
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    if acq_obj.dataset_id is None:
        return {"tile_count": 0}
    positions = (
        select(TileSQLModel.row, TileSQLModel.col)
        .where(TileSQLModel.dataset_id == acq_obj.dataset_id, TileSQLModel.run_id == acq_obj.run_id)
        .distinct()
        .subquery()
    )
    tile_count = (await session.scalars(select(func.count()).select_from(positions))).one()
    return {"tile_count": tile_count}


def _tile_sql_patch_kwargs(updated_fields: TileUpdate):
    if not updated_fields.model_fields_set:
        raise HTTPException(422, "A tile update must set at least one field")
    if _has_non_finite(updated_fields.model_dump(exclude_unset=True)):
        raise HTTPException(422, "A tile update has a NaN or infinite value")
    update_data = updated_fields.model_dump(mode="json", exclude_unset=True)
    stage_position = update_data.pop("stage_position", None)
    if stage_position is not None:
        update_data["stage_x_nm"] = stage_position["x"]
        update_data["stage_y_nm"] = stage_position["y"]
        update_data["stage_z_nm"] = stage_position.get("z")
    return update_data


@acquisition_api.patch(
    "/acquisitions/{acquisition_id}/tiles/bulk",
    response_model=list[TileResponse],
)
async def update_tile_from_acquisition_bulk(
    acquisition_id: str,
    updates: dict[str, TileUpdate] = Body(..., min_length=1),
    session: AsyncSession = Depends(get_async_session),
):
    """Update several tiles of an acquisition; nothing is applied if any tile is missing."""
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    where = _where_tiles(acq_obj, list(updates))
    tiles = (await session.scalars(select(TileSQLModel).where(*where).with_for_update())).all()
    by_tile_id = {format_tile_id(acq_obj.montage_id, tile.row, tile.col, tile.retake): tile for tile in tiles}
    missing_ids = set(updates) - set(by_tile_id)
    if missing_ids:
        listed = ", ".join(sorted(missing_ids))
        raise HTTPException(404, f"Unable to find tiles [{listed}] in acquisition '{acquisition_id}'")
    for tile_id, tile_obj in by_tile_id.items():
        update_data = _tile_sql_patch_kwargs(updates[tile_id])
        for field, value in update_data.items():
            setattr(tile_obj, field, value)
        session.add(tile_obj)
    await session.commit()
    tiles = (
        await session.scalars(
            select(TileSQLModel)
            .where(*where)
            .order_by(TileSQLModel.row, TileSQLModel.col, TileSQLModel.retake)
            .execution_options(populate_existing=True)
        )
    ).all()
    return [_tile_payload(tile_obj, acq_obj) for tile_obj in tiles]


@acquisition_api.patch(
    "/acquisitions/{acquisition_id}/tiles/{tile_id}",
    response_model=TileResponse,
)
async def update_tile_from_acquisition(
    acquisition_id: str,
    tile_id: str,
    updated_fields: TileUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific tile."""
    acquisition = await session.scalars(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    tile = await session.scalars(select(TileSQLModel).where(*_where_tile(acq_obj, tile_id)).with_for_update())
    tile_obj = tile.first()
    if tile_obj is None:
        raise HTTPException(404, f"Tile ID '{tile_id}' not found in acquisition '{acquisition_id}'")
    update_data = _tile_sql_patch_kwargs(updated_fields)
    for field, value in update_data.items():
        setattr(tile_obj, field, value)
    session.add(tile_obj)
    await session.commit()
    await session.refresh(tile_obj)
    return _tile_payload(tile_obj, acq_obj)


async def _lock_acquisition_for_tile_delete(session: AsyncSession, acquisition_id: str) -> AcquisitionSQLModel:
    acq_obj = (
        await session.scalars(
            select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id).with_for_update()
        )
    ).first()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    if acq_obj.status == "complete":
        raise HTTPException(
            409,
            (
                f"Acquisition '{acquisition_id}' is marked 'complete'; its tiles cannot be "
                "deleted. Consider archiving instead."
            ),
        )
    return acq_obj


@acquisition_api.delete("/acquisitions/{acquisition_id}/tiles/bulk", response_model=TileBulkDeleteResult)
async def delete_tiles_from_acquisition_bulk(
    acquisition_id: str,
    tile_ids: list[str] = Body(..., min_length=1),
    session: AsyncSession = Depends(get_async_session),
):
    """Delete the acquisition's tiles with these tile_ids; tile_ids not found in it are returned in not_found.

    Error if the acquisition is marked 'complete'.
    """
    acq_obj = await _lock_acquisition_for_tile_delete(session, acquisition_id)
    requested = list(dict.fromkeys(tile_ids))
    result = await session.execute(
        delete(TileSQLModel)
        .where(*_where_tiles(acq_obj, requested))
        .where(TileSQLModel.image.is_(None))
        .returning(TileSQLModel.row, TileSQLModel.col, TileSQLModel.retake)
    )
    deleted = {format_tile_id(acq_obj.montage_id, *key) for key in result.all()}
    await session.commit()
    return TileBulkDeleteResult(
        requested=len(requested),
        deleted=len(deleted),
        not_found=[tile_id for tile_id in requested if tile_id not in deleted],
    )


@acquisition_api.delete("/acquisitions/{acquisition_id}/tiles/all", response_model=TileDeleteAllResult)
async def delete_tiles_from_acquisition_all(
    acquisition_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete all tiles belonging to the specified acquisition. 409 if the acquisition is complete."""
    acq_obj = await _lock_acquisition_for_tile_delete(session, acquisition_id)
    result = await session.execute(
        delete(TileSQLModel).where(
            TileSQLModel.dataset_id == acq_obj.dataset_id,
            TileSQLModel.run_id == acq_obj.run_id,
            TileSQLModel.image.is_(None),
        )
    )
    await session.commit()
    return TileDeleteAllResult(deleted=result.rowcount)


@acquisition_api.delete(
    "/acquisitions/{acquisition_id}/tiles/{tile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tile_from_acquisition(
    acquisition_id: str,
    tile_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a specific tile of an acquisition. Error if the acquisition is complete."""
    acq_obj = await _lock_acquisition_for_tile_delete(session, acquisition_id)
    tile = await session.scalars(
        select(TileSQLModel).where(*_where_tile(acq_obj, tile_id)).where(TileSQLModel.image.is_(None))
    )
    tile_obj = tile.first()
    if tile_obj is None:
        raise HTTPException(404, f"Tile ID '{tile_id}' not found in acquisition '{acquisition_id}'")
    await session.delete(tile_obj)
    await session.commit()
    return None


@acquisition_api.get("/acquisitions/{acquisition_id}/metadata", response_model=AcquisitionFullMetadata)
async def get_acquisition_with_full_metadata(
    acquisition_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve an acquisition with its complete metadata."""
    row = (
        await session.execute(
            select(
                AcquisitionSQLModel,
                AcquisitionTaskSQLModel,
                ROISQLModel,
                SectionSQLModel,
                CuttingSessionSQLModel,
                BlockSQLModel,
                SpecimenSQLModel,
                SubstrateSQLModel,
                SpecimenSQLModel.id,
                ROISQLModel.id,
                AcquisitionTaskSQLModel.id,
            )
            .select_from(AcquisitionSQLModel)
            .outerjoin(
                AcquisitionTaskSQLModel,
                AcquisitionTaskSQLModel.task_id == AcquisitionSQLModel.acquisition_task_id,
            )
            .outerjoin(
                ROISQLModel,
                ROISQLModel.roi_id == AcquisitionSQLModel.roi_id,
            )
            .outerjoin(
                SectionSQLModel,
                SectionSQLModel.section_id == ROISQLModel.section_id,
            )
            .outerjoin(
                CuttingSessionSQLModel,
                CuttingSessionSQLModel.cutting_session_id == SectionSQLModel.cutting_session_id,
            )
            .outerjoin(
                BlockSQLModel,
                and_(
                    BlockSQLModel.block_id == CuttingSessionSQLModel.block_id,
                    BlockSQLModel.specimen_id == CuttingSessionSQLModel.specimen_id,
                ),
            )
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == AcquisitionSQLModel.specimen_id,
            )
            .outerjoin(
                SubstrateSQLModel,
                SubstrateSQLModel.media_id == ROISQLModel.substrate_media_id,
            )
            .where(AcquisitionSQLModel.acquisition_id == acquisition_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found")
    (
        acq_obj,
        task_obj,
        roi_obj,
        section_obj,
        cutting_session_obj,
        block_obj,
        specimen_obj,
        substrate_obj,
        _specimen_ref,
        _roi_ref,
        _task_ref,
    ) = row
    return AcquisitionFullMetadata(
        acquisition=AcquisitionResponse.model_validate(acq_obj),
        task=task_obj.model_dump() if task_obj else None,
        roi=roi_obj.model_dump() if roi_obj else None,
        section=section_obj.model_dump() if section_obj else None,
        cutting_session=cutting_session_obj.model_dump() if cutting_session_obj else None,
        block=block_obj.model_dump() if block_obj else None,
        specimen=specimen_obj.model_dump() if specimen_obj else None,
        substrate=substrate_obj.model_dump() if substrate_obj else None,
    )


@acquisition_api.get("/aggregated/acquisitions", response_model=dict[str, Any])
async def list_acquisitions_with_hierarchy(
    response: Response,
    cursor: int | None = Query(None, description="next_cursor of the previous page"),
    limit: int = Query(50, ge=1, le=100),
    sort_by: Literal["start_time", "acquisition_id"] = Query("start_time", description="Field to sort by"),
    sort_order: int = Query(-1, description="Sort order (-1=desc, 1=asc)"),
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    roi_id: str | None = Query(None, description="Filter by hierarchical ROI ID"),
    acquisition_task_id: str | None = Query(None, description="Filter by human-readable Acquisition Task ID"),
    substrate_media_id: str | None = Query(None, description="Filter by substrate media ID"),
    acq_status: str | None = Query(
        None,
        alias="status",
        description="Terminal status (complete, aborted, failed) or the literal 'in_flight'",
    ),
    session: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Retrieve acquisitions with complete hierarchy metadata."""
    conditions = []
    if specimen_id:
        conditions.append(AcquisitionSQLModel.specimen_id == specimen_id)
    if roi_id:
        conditions.append(AcquisitionSQLModel.roi_id == roi_id)
    if acquisition_task_id:
        conditions.append(AcquisitionSQLModel.acquisition_task_id == acquisition_task_id)
    if acq_status:
        conditions.append(_status_condition(acq_status))
    if substrate_media_id:
        conditions.append(
            AcquisitionSQLModel.roi_id.in_(
                select(ROISQLModel.roi_id).where(ROISQLModel.substrate_media_id == substrate_media_id)
            )
        )

    statement = (
        select(
            AcquisitionSQLModel,
            AcquisitionTaskSQLModel,
            ROISQLModel,
            SectionSQLModel,
            SubstrateSQLModel,
            CuttingSessionSQLModel,
            BlockSQLModel,
            SpecimenSQLModel,
        )
        .select_from(AcquisitionSQLModel)
        .outerjoin(
            AcquisitionTaskSQLModel,
            AcquisitionTaskSQLModel.task_id == AcquisitionSQLModel.acquisition_task_id,
        )
        .outerjoin(
            ROISQLModel,
            ROISQLModel.roi_id == AcquisitionSQLModel.roi_id,
        )
        .outerjoin(
            SectionSQLModel,
            SectionSQLModel.section_id == ROISQLModel.section_id,
        )
        .outerjoin(
            SubstrateSQLModel,
            SubstrateSQLModel.media_id == ROISQLModel.substrate_media_id,
        )
        .outerjoin(
            CuttingSessionSQLModel,
            CuttingSessionSQLModel.cutting_session_id == SectionSQLModel.cutting_session_id,
        )
        .outerjoin(
            BlockSQLModel,
            and_(
                BlockSQLModel.block_id == CuttingSessionSQLModel.block_id,
                BlockSQLModel.specimen_id == CuttingSessionSQLModel.specimen_id,
            ),
        )
        .outerjoin(
            SpecimenSQLModel,
            SpecimenSQLModel.specimen_id == AcquisitionSQLModel.specimen_id,
        )
    )
    rows, total_count, next_cursor = await acquisition_page(
        session, statement, conditions, sort_by, sort_order, cursor, limit
    )

    formatted_results = []
    for (
        acq,
        task_obj,
        roi_obj,
        section_obj,
        substrate_obj,
        cutting_obj,
        block_obj,
        specimen_obj,
    ) in rows:
        formatted_results.append(
            AcquisitionFullMetadata(
                acquisition=AcquisitionResponse.model_validate(acq),
                task=task_obj.model_dump() if task_obj else None,
                roi=roi_obj.model_dump() if roi_obj else None,
                section=section_obj.model_dump() if section_obj else None,
                substrate=substrate_obj.model_dump() if substrate_obj else None,
                cutting_session=cutting_obj.model_dump() if cutting_obj else None,
                block=block_obj.model_dump() if block_obj else None,
                specimen=specimen_obj.model_dump() if specimen_obj else None,
            ).model_dump(mode="json", by_alias=True)
        )
    metadata = {
        "total_count": total_count,
        "returned_count": len(formatted_results),
        "limit": limit,
        "sort_by": sort_by,
        "sort_order": sort_order if sort_order in [-1, 1] else -1,
        "next_cursor": next_cursor,
    }
    response.headers["Cache-Control"] = "private, max-age=300"
    response.headers["X-Total-Count"] = str(total_count)
    return {"acquisitions": formatted_results, "metadata": metadata}
