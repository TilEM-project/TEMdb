import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import MicroscopeCreate, MicroscopeUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.ids import uuid7
from temdb.server.sqlmodels import MicroscopeSQLModel

microscope_api = APIRouter(tags=["Microscopes"])


def _microscope_payload(scope: MicroscopeSQLModel) -> dict:
    return {
        "microscope_id": str(scope.microscope_id),
        "label": scope.label,
        "microscope_type": scope.microscope_type,
        "model": scope.model,
        "location": scope.location,
        "notes": scope.notes,
        "created_at": scope.created_at,
        "updated_at": scope.updated_at,
    }


async def _get_by_id(session: AsyncSession, microscope_id: str) -> MicroscopeSQLModel:
    try:
        key = uuid.UUID(microscope_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid microscope_id '{microscope_id}'")
    scope = (
        await session.exec(select(MicroscopeSQLModel).where(MicroscopeSQLModel.microscope_id == key))
    ).one_or_none()
    if scope is None:
        raise HTTPException(status_code=404, detail=f"Microscope '{microscope_id}' not found")
    return scope


@microscope_api.post("/microscopes", status_code=status.HTTP_201_CREATED)
async def create_microscope(data: MicroscopeCreate, session: AsyncSession = Depends(get_async_session)):
    existing = (
        await session.exec(select(MicroscopeSQLModel).where(MicroscopeSQLModel.label == data.label))
    ).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"Microscope label '{data.label}' already exists")
    scope = MicroscopeSQLModel(
        microscope_id=data.microscope_id if data.microscope_id is not None else uuid7(),
        label=data.label,
        microscope_type=data.microscope_type,
        model=data.model,
        location=data.location,
        notes=data.notes,
        created_at=datetime.now(timezone.utc),
    )
    session.add(scope)
    await session.commit()
    await session.refresh(scope)
    return _microscope_payload(scope)


@microscope_api.get("/microscopes")
async def list_microscopes(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    rows = (
        await session.exec(select(MicroscopeSQLModel).order_by(MicroscopeSQLModel.label).offset(skip).limit(limit))
    ).all()
    return [_microscope_payload(scope) for scope in rows]


@microscope_api.get("/microscopes/{id_or_label}")
async def get_microscope(id_or_label: str, session: AsyncSession = Depends(get_async_session)):
    try:
        key = uuid.UUID(id_or_label)
    except ValueError:
        scope = (
            await session.exec(select(MicroscopeSQLModel).where(MicroscopeSQLModel.label == id_or_label))
        ).one_or_none()
        if scope is None:
            raise HTTPException(status_code=404, detail=f"Microscope '{id_or_label}' not found")
        return _microscope_payload(scope)
    return _microscope_payload(await _get_by_id(session, str(key)))


@microscope_api.patch("/microscopes/{microscope_id}")
async def update_microscope(
    microscope_id: str,
    updated: MicroscopeUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    scope = await _get_by_id(session, microscope_id)
    data = updated.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No update data provided")
    for field, value in data.items():
        setattr(scope, field, value)
    scope.updated_at = datetime.now(timezone.utc)
    session.add(scope)
    await session.commit()
    await session.refresh(scope)
    return _microscope_payload(scope)
