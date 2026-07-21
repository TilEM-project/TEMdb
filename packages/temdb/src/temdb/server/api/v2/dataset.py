import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import DatasetCreate, DatasetResponse, DatasetUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.ids import uuid7
from temdb.server.sqlmodels import DatasetSQLModel
from temdb.server.sqlmodels.tile_partition import resolve_size_class

dataset_api = APIRouter(tags=["Datasets"])


async def _get_by_id(session: AsyncSession, dataset_id: str) -> DatasetSQLModel:
    try:
        key = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid dataset_id '{dataset_id}'")
    ds = (await session.scalars(select(DatasetSQLModel).where(DatasetSQLModel.dataset_id == key))).one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return ds


@dataset_api.post("/datasets", status_code=status.HTTP_201_CREATED, response_model=DatasetResponse)
async def create_dataset(data: DatasetCreate, session: AsyncSession = Depends(get_async_session)):
    existing = (await session.scalars(select(DatasetSQLModel).where(DatasetSQLModel.name == data.name))).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail=f"Dataset name '{data.name}' already exists")
    if data.parent_dataset_id is not None:
        parent = (
            await session.scalars(select(DatasetSQLModel).where(DatasetSQLModel.dataset_id == data.parent_dataset_id))
        ).one_or_none()
        if parent is None:
            raise HTTPException(status_code=404, detail=f"Parent dataset '{data.parent_dataset_id}' not found")
        if parent.parent_dataset_id is not None:
            raise HTTPException(
                status_code=400,
                detail=f"Dataset '{parent.dataset_id}' is itself a child; nesting is one level only",
            )
    if data.size_class is not None:
        size_class = data.size_class
    elif data.estimated_tile_count is not None:
        size_class = resolve_size_class(data.estimated_tile_count)
    else:
        raise HTTPException(status_code=400, detail="Provide size_class or estimated_tile_count")
    ds = DatasetSQLModel(
        dataset_id=uuid7(),
        name=data.name,
        description=data.description,
        specimen_id=data.specimen_id,
        parent_dataset_id=data.parent_dataset_id,
        size_class=size_class,
        estimated_tile_count=data.estimated_tile_count,
        metadata_json=data.metadata_json,
        created_at=data.created_at or datetime.now(timezone.utc),
    )
    session.add(ds)
    await session.commit()
    await session.refresh(ds)
    return ds


@dataset_api.get("/datasets", response_model=list[DatasetResponse])
async def list_datasets(
    specimen_id: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    parent_dataset_id: uuid.UUID | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = select(DatasetSQLModel)
    if specimen_id is not None:
        stmt = stmt.where(DatasetSQLModel.specimen_id == specimen_id)
    if status_filter is not None:
        stmt = stmt.where(DatasetSQLModel.status == status_filter)
    if parent_dataset_id is not None:
        stmt = stmt.where(DatasetSQLModel.parent_dataset_id == parent_dataset_id)
    rows = (await session.scalars(stmt.order_by(DatasetSQLModel.created_at).offset(skip).limit(limit))).all()
    return rows


@dataset_api.get("/datasets/by-name/{name}", response_model=DatasetResponse)
async def get_dataset_by_name(name: str, session: AsyncSession = Depends(get_async_session)):
    ds = (await session.scalars(select(DatasetSQLModel).where(DatasetSQLModel.name == name))).one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset name '{name}' not found")
    return ds


@dataset_api.get("/datasets/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str, session: AsyncSession = Depends(get_async_session)):
    return await _get_by_id(session, dataset_id)


@dataset_api.get("/datasets/{dataset_id}/children", response_model=list[DatasetResponse])
async def list_dataset_children(dataset_id: str, session: AsyncSession = Depends(get_async_session)):
    parent = await _get_by_id(session, dataset_id)
    rows = (
        await session.scalars(
            select(DatasetSQLModel)
            .where(DatasetSQLModel.parent_dataset_id == parent.dataset_id)
            .order_by(DatasetSQLModel.created_at)
        )
    ).all()
    return rows


@dataset_api.patch("/datasets/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: str,
    updated: DatasetUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    ds = await _get_by_id(session, dataset_id)
    data = updated.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="No update data provided")
    now = datetime.now(timezone.utc)
    status_changed = "status" in data and data["status"] != ds.status
    for field, value in data.items():
        if field == "status":
            continue
        setattr(ds, field, value)
    if status_changed:
        ds.status = data["status"]
        if ds.status == "collected" and ds.collected_at is None:
            ds.collected_at = now
        if ds.status == "archived" and ds.archived_at is None:
            ds.archived_at = now
    ds.updated_at = now
    session.add(ds)
    await session.commit()
    await session.refresh(ds)
    return ds
