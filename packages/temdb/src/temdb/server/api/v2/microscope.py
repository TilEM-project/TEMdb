from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import MicroscopeCreate, MicroscopeResponse, MicroscopeUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import MicroscopeSQLModel

from ..utils import drop_null_keys, merge_extra

microscope_api = APIRouter(tags=["Microscopes"])


async def _get_by_id(session: AsyncSession, microscope_id: str) -> MicroscopeSQLModel:
    scope = await session.scalar(select(MicroscopeSQLModel).where(MicroscopeSQLModel.microscope_id == microscope_id))
    if scope is None:
        raise HTTPException(status_code=404, detail=f"Microscope '{microscope_id}' not found")
    return scope


@microscope_api.post("/microscopes", status_code=status.HTTP_201_CREATED, response_model=MicroscopeResponse)
async def create_microscope(data: MicroscopeCreate, session: AsyncSession = Depends(get_async_session)):
    existing = (
        await session.scalars(select(MicroscopeSQLModel).where(MicroscopeSQLModel.microscope_id == data.microscope_id))
    ).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Microscope '{data.microscope_id}' already exists")
    scope = MicroscopeSQLModel(
        microscope_id=data.microscope_id,
        microscope_type=data.microscope_type,
        model=data.model,
        location=data.location,
        notes=data.notes,
        created_at=data.created_at or datetime.now(timezone.utc),
        extra=drop_null_keys(data.extra),
    )
    session.add(scope)
    await session.commit()
    await session.refresh(scope)
    return scope


@microscope_api.get("/microscopes", response_model=list[MicroscopeResponse])
async def list_microscopes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    rows = (
        await session.scalars(
            select(MicroscopeSQLModel).order_by(MicroscopeSQLModel.microscope_id).offset(skip).limit(limit)
        )
    ).all()
    return rows


@microscope_api.get("/microscopes/{microscope_id}", response_model=MicroscopeResponse)
async def get_microscope(microscope_id: str, session: AsyncSession = Depends(get_async_session)):
    return await _get_by_id(session, microscope_id)


@microscope_api.patch("/microscopes/{microscope_id}", response_model=MicroscopeResponse)
async def update_microscope(
    microscope_id: str,
    updated: MicroscopeUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    scope = await _get_by_id(session, microscope_id)
    data = updated.model_dump(
        exclude_unset=True,
    )
    if not data:
        raise HTTPException(status_code=400, detail="No update data provided")
    extra_changes = data.pop("extra", None)
    for field, value in data.items():
        setattr(scope, field, value)
    if extra_changes is not None:
        scope.extra = merge_extra(MicroscopeSQLModel.extra, extra_changes)
    scope.updated_at = datetime.now(timezone.utc)
    session.add(scope)
    await session.commit()
    await session.refresh(scope)
    return scope
