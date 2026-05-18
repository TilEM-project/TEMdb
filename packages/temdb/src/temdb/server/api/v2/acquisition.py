import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import (
    AcquisitionCreate,
    AcquisitionStatus,
    AcquisitionUpdate,
    StorageLocation,
    StorageLocationCreate,
    TileCreate,
)
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import (
    AcquisitionSQLModel,
    AcquisitionTaskSQLModel,
    BlockSQLModel,
    CuttingSessionSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SpecimenSQLModel,
    SubstrateSQLModel,
    TileSQLModel,
)

acquisition_api = APIRouter(
    tags=["Acquisitions"],
)

logger = logging.getLogger(__name__)


def _ref_payload(value: int | None) -> dict[str, str] | None:
    return {"id": str(value)} if value is not None else None


def _acquisition_payload(
    acquisition: AcquisitionSQLModel,
    specimen_internal_id: int | None = None,
    roi_internal_id: int | None = None,
    task_internal_id: int | None = None,
) -> dict[str, Any]:
    payload = acquisition.model_dump()
    payload["_id"] = str(acquisition.id)
    payload["specimen_ref"] = _ref_payload(specimen_internal_id)
    payload["roi_ref"] = _ref_payload(roi_internal_id)
    payload["acquisition_task_ref"] = _ref_payload(task_internal_id)
    return payload


def _tile_payload(tile: TileSQLModel, acquisition_internal_id: int | None = None) -> dict[str, Any]:
    payload = tile.model_dump()
    payload["_id"] = str(tile.id)
    payload["acquisition_ref"] = _ref_payload(acquisition_internal_id)
    return payload


@acquisition_api.get("/acquisitions", response_model=dict[str, Any])
async def list_acquisitions(
    response: Response,
    cursor: str | None = Query(
        None,
        description="Cursor for pagination (e.g., last seen acquisition_id or _id)",
    ),
    limit: int = Query(50, ge=1, le=1000),
    sort_by: str = Query("start_time", description="Field to sort by (e.g., start_time, acquisition_id)"),
    sort_order: int = Query(-1, description="Sort order (-1=desc, 1=asc)"),
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    roi_id: str | None = Query(None, description="Filter by human-readable ROI ID"),
    acquisition_task_id: str | None = Query(None, description="Filter by human-readable Acquisition Task ID"),
    montage_set_name: str | None = Query(None),
    magnification: int | None = Query(None, ge=1),
    acq_status: AcquisitionStatus | None = Query(None, alias="status"),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    param_tile_focus_lt: float | None = Query(
        None,
        description="Filter acquisitions where tile focus score is less than this value",
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
    """Retrieve a list of acquisitions with filtering, sorting, and pagination."""
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
        conditions.append(AcquisitionSQLModel.status == acq_status.value)
    if start_date:
        conditions.append(AcquisitionSQLModel.start_time >= start_date)
    if end_date:
        conditions.append(AcquisitionSQLModel.start_time <= end_date)
    if param_tile_focus_lt is not None:
        acq_ids = (
            await session.exec(
                select(TileSQLModel.acquisition_id).where(TileSQLModel.focus_score < param_tile_focus_lt)
            )
        ).all()
        if not acq_ids:
            metadata = {
                "total_count": 0,
                "returned_count": 0,
                "limit": limit,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "next_cursor": None,
            }
            return {"acquisitions": [], "metadata": metadata}
        conditions.append(AcquisitionSQLModel.acquisition_id.in_(set(acq_ids)))

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

    sort_column = getattr(AcquisitionSQLModel, sort_by, AcquisitionSQLModel.start_time)
    order_column = sort_column.asc() if sort_order == 1 else sort_column.desc()
    rows = (
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
            .where(*conditions)
            .order_by(order_column)
        )
    ).all()
    acquisitions = [row[0] for row in rows]
    if magnification is not None:
        rows = [
            row
            for row in rows
            if isinstance(row[0].acquisition_settings, dict)
            and row[0].acquisition_settings.get("magnification") == magnification
        ]
        acquisitions = [row[0] for row in rows]
    total_count = len(acquisitions)
    rows = rows[:limit]
    payloads = []
    for acq, specimen_ref, roi_ref, task_ref in rows:
        payload = _acquisition_payload(acq, specimen_ref, roi_ref, task_ref)
        if fields:
            kept = {field: payload.get(field) for field in fields}
            kept["_id"] = payload["_id"]
            payload = kept
        payloads.append(payload)
    next_cursor = str(rows[-1][0].id) if rows else None
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


@acquisition_api.post("/acquisitions", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_acquisition(
    acq_data: AcquisitionCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new acquisition with validation but without transactions."""
    existing = await session.exec(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acq_data.acquisition_id)
    )
    if existing.first() is not None:
        raise HTTPException(400, f"Acquisition ID '{acq_data.acquisition_id}' already exists.")
    task_and_roi = (
        await session.execute(
            select(
                AcquisitionTaskSQLModel,
                ROISQLModel,
                SpecimenSQLModel.id,
                ROISQLModel.id,
                AcquisitionTaskSQLModel.id,
            )
            .select_from(AcquisitionTaskSQLModel)
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == AcquisitionTaskSQLModel.specimen_id,
            )
            .outerjoin(ROISQLModel, ROISQLModel.roi_id == acq_data.roi_id)
            .where(AcquisitionTaskSQLModel.task_id == acq_data.acquisition_task_id)
        )
    ).first()
    task_obj = task_and_roi[0] if task_and_roi else None
    if task_obj is None:
        raise HTTPException(404, f"Acquisition Task '{acq_data.acquisition_task_id}' not found.")
    roi_obj = task_and_roi[1]
    if roi_obj is None:
        raise HTTPException(404, f"ROI '{acq_data.roi_id}' not found.")
    if task_obj.roi_id != roi_obj.roi_id:
        raise HTTPException(
            400,
            f"ROI ID '{roi_obj.roi_id}' does not match ROI reference in Task '{task_obj.task_id}'.",
        )
    replacement_id = None
    if acq_data.replaces_acquisition_id:
        replacement = await session.exec(
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
    acquisition = AcquisitionSQLModel(
        acquisition_id=acq_data.acquisition_id,
        montage_id=acq_data.montage_id,
        specimen_id=task_obj.specimen_id,
        roi_id=roi_obj.roi_id,
        acquisition_task_id=task_obj.task_id,
        hardware_settings=acq_data.hardware_settings.model_dump(),
        acquisition_settings=acq_data.acquisition_settings.model_dump(),
        calibration_info=acq_data.calibration_info.model_dump() if acq_data.calibration_info else None,
        status=acq_data.status.value,
        tilt_angle=acq_data.tilt_angle,
        lens_correction=acq_data.lens_correction,
        start_time=acq_data.start_time or datetime.now(timezone.utc),
        end_time=acq_data.end_time,
        storage_locations=(
            [loc.model_dump(mode="json") for loc in acq_data.storage_locations] if acq_data.storage_locations else None
        ),
        montage_set_name=acq_data.montage_set_name,
        sub_region=acq_data.sub_region.model_dump(mode="json") if acq_data.sub_region else None,
        replaces_acquisition_id=replacement_id,
    )
    session.add(acquisition)
    await session.commit()
    await session.refresh(acquisition)
    specimen_ref, roi_ref, task_ref = task_and_roi[2], task_and_roi[3], task_and_roi[4]
    return _acquisition_payload(acquisition, specimen_ref, roi_ref, task_ref)


@acquisition_api.get("/acquisitions/{acquisition_id}", response_model=dict[str, Any])
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
    acq_obj, specimen_ref, roi_ref, task_ref = row
    return _acquisition_payload(acq_obj, specimen_ref, roi_ref, task_ref)


@acquisition_api.patch("/acquisitions/{acquisition_id}", response_model=dict[str, Any])
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
    acq_obj, specimen_ref, roi_ref, task_ref = row
    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(400, "No update data provided")
    for field, value in update_data.items():
        if hasattr(acq_obj, field):
            if hasattr(value, "model_dump"):
                setattr(acq_obj, field, value.model_dump(mode="json"))
            else:
                setattr(acq_obj, field, value.value if hasattr(value, "value") else value)
    session.add(acq_obj)
    await session.commit()
    await session.refresh(acq_obj)
    return _acquisition_payload(acq_obj, specimen_ref, roi_ref, task_ref)


@acquisition_api.delete("/acquisitions/{acquisition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_acquisition(
    acquisition_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a specific acquisition."""
    acquisition = await session.exec(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found")
    tile_count = (
        await session.exec(
            select(func.count()).select_from(TileSQLModel).where(TileSQLModel.acquisition_id == acquisition_id)
        )
    ).one()
    if tile_count > 0:
        raise HTTPException(
            400,
            f"Cannot delete acquisition '{acquisition_id}': {tile_count} tiles exist.",
        )
    await session.delete(acq_obj)
    await session.commit()
    return None


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
    acquisition = await session.exec(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found")
    existing = await session.exec(select(TileSQLModel).where(TileSQLModel.tile_id == tile_data.tile_id))
    if existing.first() is not None:
        raise HTTPException(400, f"Tile ID '{tile_data.tile_id}' already exists.")
    tile = TileSQLModel(
        **tile_data.model_dump(),
        acquisition_id=acq_obj.acquisition_id,
    )
    session.add(tile)
    await session.commit()
    await session.refresh(tile)
    return _tile_payload(tile, acq_obj.id)


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
    total_tiles = len(tiles)
    incoming_tile_ids = [t.tile_id for t in tiles]
    existing_ids = (
        await session.exec(select(TileSQLModel.tile_id).where(TileSQLModel.tile_id.in_(incoming_tile_ids)))
    ).all()
    existing_set = set(existing_ids)
    docs_to_insert = [
        TileSQLModel(
            **tile.model_dump(),
            acquisition_id=acq_obj.acquisition_id,
        )
        for tile in tiles
        if tile.tile_id not in existing_set
    ]
    if docs_to_insert:
        session.add_all(docs_to_insert)
        await session.commit()
    return {
        "acquisition_id": acquisition_id,
        "total_received": total_tiles,
        "inserted": len(docs_to_insert),
        "skipped_existing": len(existing_set),
    }


@acquisition_api.get("/acquisitions/{acquisition_id}/tiles", response_model=dict[str, Any])
async def get_tiles_from_acquisition(
    response: Response,
    acquisition_id: str,
    cursor: int | None = Query(None, description="Last raster_index seen"),
    limit: int = Query(100, ge=1, le=1000),
    fields: list[str] | None = Query(None),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve tiles associated with a specific acquisition."""
    acquisition = await session.exec(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    query = select(TileSQLModel).where(TileSQLModel.acquisition_id == acquisition_id)
    if cursor is not None:
        query = query.where(TileSQLModel.raster_index > cursor)
    query = query.order_by(TileSQLModel.raster_index).limit(limit + 1)
    rows = (await session.exec(query)).all()
    has_more = len(rows) > limit
    tiles = rows[:limit]
    payloads = [_tile_payload(tile, acq_obj.id) for tile in tiles]
    if fields:
        trimmed = []
        for payload in payloads:
            entry = {field: payload.get(field) for field in fields}
            entry["raster_index"] = payload.get("raster_index")
            trimmed.append(entry)
        payloads = trimmed
    next_cursor = tiles[-1].raster_index if tiles else None
    response.headers["Cache-Control"] = "private, max-age=300"
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


@acquisition_api.get("/acquisitions/{acquisition_id}/tiles/{tile_id}", response_model=dict[str, Any])
async def get_tile_from_acquisition(
    acquisition_id: str,
    tile_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a specific tile by its human-readable ID, verifying acquisition parent."""
    acquisition = await session.exec(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    tile = await session.exec(
        select(TileSQLModel).where(
            TileSQLModel.tile_id == tile_id,
            TileSQLModel.acquisition_id == acquisition_id,
        )
    )
    tile_obj = tile.first()
    if tile_obj is None:
        raise HTTPException(404, f"Tile ID '{tile_id}' not found in acquisition '{acquisition_id}'")
    return _tile_payload(tile_obj, acq_obj.id)


def _current_storage_location(storage_locations: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    if not storage_locations:
        return None
    return next((loc for loc in storage_locations if loc.get("is_current")), None)


@acquisition_api.post("/acquisitions/{acquisition_id}/storage-locations", response_model=dict[str, Any])
async def add_storage_location(
    acquisition_id: str,
    storage_location: StorageLocationCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Add a storage location entry to an acquisition."""
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

    new_location = storage_location.model_dump(mode="json")
    make_current = new_location.get("is_current", True)
    new_location["is_current"] = make_current
    if not new_location.get("date_added"):
        new_location["date_added"] = datetime.now(timezone.utc).isoformat()

    existing_locations = list(acq_obj.storage_locations or [])
    if make_current:
        for loc in existing_locations:
            if isinstance(loc, dict):
                loc["is_current"] = False
    existing_locations.append(new_location)

    acq_obj.storage_locations = existing_locations
    session.add(acq_obj)
    await session.commit()
    await session.refresh(acq_obj)
    return _acquisition_payload(acq_obj, specimen_ref, roi_ref, task_ref)


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/current-storage",
    response_model=StorageLocation | None,
)
async def get_current_storage_location(
    acquisition_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get the current storage location for an acquisition."""
    acquisition = await session.exec(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    return _current_storage_location(acq_obj.storage_locations)


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/minimap-uri",
    response_model=dict[str, str | None],
)
async def get_minimap_uri(
    acquisition_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get the calculated URI for the acquisition's minimap image."""
    acquisition = await session.exec(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    acq_obj = acquisition.first()
    if acq_obj is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    current_location = _current_storage_location(acq_obj.storage_locations)
    base_path = current_location.get("base_path") if current_location else None
    return {"minimap_uri": f"{base_path}/minimap.png" if base_path else None}


@acquisition_api.get("/acquisitions/{acquisition_id}/tile-count", response_model=dict[str, int])
async def get_tile_count(
    acquisition_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Get the total count of tiles associated with an acquisition."""
    acquisition = await session.exec(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    if acquisition.first() is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    tile_count = (
        await session.exec(
            select(func.count()).select_from(TileSQLModel).where(TileSQLModel.acquisition_id == acquisition_id)
        )
    ).one()
    return {"tile_count": tile_count}


@acquisition_api.delete(
    "/acquisitions/{acquisition_id}/tiles/{tile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tile_from_acquisition(
    acquisition_id: str,
    tile_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a specific tile, ensuring it belongs to the specified acquisition."""
    acquisition = await session.exec(
        select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == acquisition_id)
    )
    if acquisition.first() is None:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    tile = await session.exec(
        select(TileSQLModel).where(
            TileSQLModel.tile_id == tile_id,
            TileSQLModel.acquisition_id == acquisition_id,
        )
    )
    tile_obj = tile.first()
    if tile_obj is None:
        raise HTTPException(404, f"Tile ID '{tile_id}' not found in acquisition '{acquisition_id}'")
    await session.delete(tile_obj)
    await session.commit()
    return None


class AcquisitionFullMetadata(BaseModel):
    """Acquisition with complete hierarchy metadata"""

    acquisition: dict[str, Any]
    acquisition_task: dict[str, Any] | None = None
    roi: dict[str, Any] | None = None
    section: dict[str, Any] | None = None
    cutting_session: dict[str, Any] | None = None
    block: dict[str, Any] | None = None
    specimen: dict[str, Any] | None = None
    substrate: dict[str, Any] | None = None


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
        specimen_ref,
        roi_ref,
        task_ref,
    ) = row
    return {
        "acquisition": _acquisition_payload(acq_obj, specimen_ref, roi_ref, task_ref),
        "acquisition_task": task_obj.model_dump() if task_obj else None,
        "roi": roi_obj.model_dump() if roi_obj else None,
        "section": section_obj.model_dump() if section_obj else None,
        "cutting_session": cutting_session_obj.model_dump() if cutting_session_obj else None,
        "block": block_obj.model_dump() if block_obj else None,
        "specimen": specimen_obj.model_dump() if specimen_obj else None,
        "substrate": substrate_obj.model_dump() if substrate_obj else None,
    }


@acquisition_api.get("/aggregated/acquisitions", response_model=dict[str, Any])
async def list_acquisitions_with_hierarchy(
    response: Response,
    cursor: str | None = Query(
        None,
        description="Cursor for pagination (e.g., last seen acquisition_id or _id)",
    ),
    limit: int = Query(50, ge=1, le=100),
    sort_by: str = Query("start_time", description="Field to sort by (e.g., start_time, acquisition_id)"),
    sort_order: int = Query(-1, description="Sort order (-1=desc, 1=asc)"),
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    roi_id: str | None = Query(None, description="Filter by hierarchical ROI ID"),
    acquisition_task_id: str | None = Query(None, description="Filter by human-readable Acquisition Task ID"),
    substrate_media_id: str | None = Query(None, description="Filter by substrate media ID"),
    acq_status: AcquisitionStatus | None = Query(None, alias="status"),
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
        conditions.append(AcquisitionSQLModel.status == acq_status.value)
    if substrate_media_id:
        conditions.append(SubstrateSQLModel.media_id == substrate_media_id)

    sort_column = getattr(AcquisitionSQLModel, sort_by, AcquisitionSQLModel.start_time)
    order_column = sort_column.asc() if sort_order == 1 else sort_column.desc()
    rows = (
        await session.execute(
            select(
                AcquisitionSQLModel,
                AcquisitionTaskSQLModel,
                ROISQLModel,
                SectionSQLModel,
                SubstrateSQLModel,
                CuttingSessionSQLModel,
                BlockSQLModel,
                SpecimenSQLModel,
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
            .where(*conditions)
            .order_by(order_column)
        )
    ).all()

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
        specimen_ref,
        roi_ref_value,
        task_ref,
    ) in rows:
        formatted_results.append(
            {
                "acquisition": _acquisition_payload(acq, specimen_ref, roi_ref_value, task_ref),
                "acquisition_task": task_obj.model_dump() if task_obj else None,
                "roi": roi_obj.model_dump() if roi_obj else None,
                "section": section_obj.model_dump() if section_obj else None,
                "substrate": substrate_obj.model_dump() if substrate_obj else None,
                "cutting_session": cutting_obj.model_dump() if cutting_obj else None,
                "block": block_obj.model_dump() if block_obj else None,
                "specimen": specimen_obj.model_dump() if specimen_obj else None,
            }
        )
    total_count = len(formatted_results)
    formatted_results = formatted_results[:limit]
    next_cursor = str(formatted_results[-1]["acquisition"].get("_id")) if formatted_results else None
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
