import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import DatasetCreate, DatasetUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.ids import uuid7
from temdb.server.sqlmodels import DatasetSQLModel
from temdb.server.sqlmodels.tile_partition import resolve_size_class

dataset_api = APIRouter(tags=["Datasets"])


def _dataset_payload(ds: DatasetSQLModel) -> dict:
    return {
        "dataset_id": str(ds.dataset_id),
        "name": ds.name,
        "description": ds.description,
        "specimen_id": ds.specimen_id,
        "parent_dataset_id": str(ds.parent_dataset_id) if ds.parent_dataset_id is not None else None,
        "status": ds.status,
        "size_class": ds.size_class,
        "estimated_tile_count": ds.estimated_tile_count,
        "tile_hash_modulus": ds.tile_hash_modulus,
        "collected_at": ds.collected_at,
        "archived_at": ds.archived_at,
        "metadata_json": ds.metadata_json,
        "created_at": ds.created_at,
        "updated_at": ds.updated_at,
    }


async def _get_by_id(session: AsyncSession, dataset_id: str) -> DatasetSQLModel:
    try:
        key = uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid dataset_id '{dataset_id}'")
    ds = (await session.exec(select(DatasetSQLModel).where(DatasetSQLModel.dataset_id == key))).one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found")
    return ds


@dataset_api.post("/datasets", status_code=status.HTTP_201_CREATED)
async def create_dataset(data: DatasetCreate, session: AsyncSession = Depends(get_async_session)):
    existing = (await session.exec(select(DatasetSQLModel).where(DatasetSQLModel.name == data.name))).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail=f"Dataset name '{data.name}' already exists")
    if data.parent_dataset_id is not None:
        parent = (
            await session.exec(select(DatasetSQLModel).where(DatasetSQLModel.dataset_id == data.parent_dataset_id))
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
    return _dataset_payload(ds)


@dataset_api.get("/datasets")
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
    rows = (await session.exec(stmt.order_by(DatasetSQLModel.created_at).offset(skip).limit(limit))).all()
    return [_dataset_payload(ds) for ds in rows]


@dataset_api.get("/datasets/by-name/{name}")
async def get_dataset_by_name(name: str, session: AsyncSession = Depends(get_async_session)):
    ds = (await session.exec(select(DatasetSQLModel).where(DatasetSQLModel.name == name))).one_or_none()
    if ds is None:
        raise HTTPException(status_code=404, detail=f"Dataset name '{name}' not found")
    return _dataset_payload(ds)


@dataset_api.get("/datasets/{dataset_id}")
async def get_dataset(dataset_id: str, session: AsyncSession = Depends(get_async_session)):
    return _dataset_payload(await _get_by_id(session, dataset_id))


@dataset_api.get("/datasets/{dataset_id}/children")
async def list_dataset_children(dataset_id: str, session: AsyncSession = Depends(get_async_session)):
    parent = await _get_by_id(session, dataset_id)
    rows = (
        await session.exec(
            select(DatasetSQLModel)
            .where(DatasetSQLModel.parent_dataset_id == parent.dataset_id)
            .order_by(DatasetSQLModel.created_at)
        )
    ).all()
    return [_dataset_payload(ds) for ds in rows]


@dataset_api.patch("/datasets/{dataset_id}")
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
    if "description" in data:
        ds.description = data["description"]
    if "size_class" in data:
        ds.size_class = data["size_class"]
    if "metadata_json" in data:
        ds.metadata_json = data["metadata_json"]
    if "status" in data and data["status"] != ds.status:
        ds.status = data["status"]
        if ds.status == "collected" and ds.collected_at is None:
            ds.collected_at = now
        if ds.status == "archived" and ds.archived_at is None:
            ds.archived_at = now
    ds.updated_at = now
    session.add(ds)
    await session.commit()
    await session.refresh(ds)
    return _dataset_payload(ds)
