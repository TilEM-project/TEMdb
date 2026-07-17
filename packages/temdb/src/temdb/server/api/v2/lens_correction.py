import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import LensCorrectionCreate, LensCorrectionUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.ids import uuid7
from temdb.server.sqlmodels import LensCorrectionSQLModel, MicroscopeSQLModel

lens_correction_api = APIRouter(tags=["Lens Corrections"])


def _lens_correction_payload(lc: LensCorrectionSQLModel) -> dict:
    return {
        "lc_id": str(lc.lc_id),
        "microscope_id": str(lc.microscope_id),
        "magnification": lc.magnification,
        "started_at": lc.started_at,
        "source_run_id": str(lc.source_run_id) if lc.source_run_id is not None else None,
        "source_dataset_id": str(lc.source_dataset_id) if lc.source_dataset_id is not None else None,
        "shared_transform": lc.shared_transform,
        "correction_x_uri": lc.correction_x_uri,
        "correction_y_uri": lc.correction_y_uri,
        "solver_params": lc.solver_params,
        "created_at": lc.created_at,
        "updated_at": lc.updated_at,
    }


async def _get_by_id(session: AsyncSession, lc_id: str) -> LensCorrectionSQLModel:
    try:
        key = uuid.UUID(lc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid lc_id '{lc_id}'")
    lc = (
        await session.exec(select(LensCorrectionSQLModel).where(LensCorrectionSQLModel.lc_id == key))
    ).one_or_none()
    if lc is None:
        raise HTTPException(status_code=404, detail=f"Lens correction '{lc_id}' not found")
    return lc


@lens_correction_api.post("/lens-corrections", status_code=status.HTTP_201_CREATED)
async def create_lens_correction(data: LensCorrectionCreate, session: AsyncSession = Depends(get_async_session)):
    microscope = (
        await session.exec(
            select(MicroscopeSQLModel).where(MicroscopeSQLModel.microscope_id == data.microscope_id)
        )
    ).one_or_none()
    if microscope is None:
        raise HTTPException(status_code=404, detail=f"Microscope '{data.microscope_id}' not found")
    lc = LensCorrectionSQLModel(
        lc_id=data.lc_id if data.lc_id is not None else uuid7(),
        microscope_id=data.microscope_id,
        magnification=data.magnification,
        started_at=data.started_at,
        source_run_id=data.source_run_id,
        source_dataset_id=data.source_dataset_id,
        shared_transform=data.shared_transform,
        correction_x_uri=data.correction_x_uri,
        correction_y_uri=data.correction_y_uri,
        solver_params=data.solver_params,
        created_at=data.created_at or datetime.now(timezone.utc),
    )
    session.add(lc)
    await session.commit()
    await session.refresh(lc)
    return _lens_correction_payload(lc)


@lens_correction_api.get("/lens-corrections")
async def list_lens_corrections(
    microscope_id: uuid.UUID | None = Query(None),
    magnification: int | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(LensCorrectionSQLModel)
    if microscope_id is not None:
        stmt = stmt.where(LensCorrectionSQLModel.microscope_id == microscope_id)
    if magnification is not None:
        stmt = stmt.where(LensCorrectionSQLModel.magnification == magnification)
    rows = (
        await session.exec(
            stmt.order_by(LensCorrectionSQLModel.started_at.desc()).offset(skip).limit(limit)
        )
    ).all()
    return [_lens_correction_payload(lc) for lc in rows]


# NOTE: /current must be declared before /{lc_id} so the literal path wins.
@lens_correction_api.get("/lens-corrections/current")
async def get_current_lens_correction(
    microscope_id: uuid.UUID = Query(...),
    magnification: int = Query(...),
    session: AsyncSession = Depends(get_async_session),
):
    lc = (
        await session.exec(
            select(LensCorrectionSQLModel)
            .where(LensCorrectionSQLModel.microscope_id == microscope_id)
            .where(LensCorrectionSQLModel.magnification == magnification)
            .order_by(LensCorrectionSQLModel.started_at.desc())
            .limit(1)
        )
    ).one_or_none()
    if lc is None:
        raise HTTPException(
            status_code=404,
            detail=f"No lens correction for microscope '{microscope_id}' at magnification {magnification}",
        )
    return _lens_correction_payload(lc)


@lens_correction_api.get("/lens-corrections/{lc_id}")
async def get_lens_correction(lc_id: str, session: AsyncSession = Depends(get_async_session)):
    return _lens_correction_payload(await _get_by_id(session, lc_id))


@lens_correction_api.patch("/lens-corrections/{lc_id}")
async def update_lens_correction(
    lc_id: str,
    updated: LensCorrectionUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    lc = await _get_by_id(session, lc_id)
    data = updated.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No update data provided")
    for field, value in data.items():
        setattr(lc, field, value)
    lc.updated_at = datetime.now(timezone.utc)
    session.add(lc)
    await session.commit()
    await session.refresh(lc)
    return _lens_correction_payload(lc)
