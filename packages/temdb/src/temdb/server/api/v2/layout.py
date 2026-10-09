from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import (
    SubstrateLayoutCreate,
    SubstrateLayoutResponse,
    SubstrateLayoutUpdate,
    SubstrateResponse,
    SubstrateType,
)
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import SubstrateLayoutSQLModel, SubstrateSQLModel

substrate_layout_api = APIRouter(
    tags=["Layouts"],
)


def _to_json_compatible(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return jsonable_encoder(value)


@substrate_layout_api.get("/layouts", response_model=list[SubstrateLayoutResponse])
async def list_layouts(
    media_type: SubstrateType | None = Query(
        None, description="Filter by substrate media type (e.g., 'wafer', 'tape')"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of substrates with optional filters and pagination."""
    statement = select(SubstrateLayoutSQLModel)
    if media_type:
        statement = statement.where(SubstrateLayoutSQLModel.media_type == media_type)
    layouts = (await session.scalars(statement.offset(skip).limit(limit))).all()
    return layouts


@substrate_layout_api.post("/layouts", status_code=status.HTTP_201_CREATED, response_model=SubstrateLayoutResponse)
async def create_layout(
    layout_data: SubstrateLayoutCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new substrate."""
    existing_layout = await session.scalars(
        select(SubstrateLayoutSQLModel).where(SubstrateLayoutSQLModel.layout_id == layout_data.layout_id)
    )
    if existing_layout.one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Substrate layout with layout_id '{layout_data.layout_id}' already exists.",
        )
    new_layout = SubstrateLayoutSQLModel(
        layout_id=layout_data.layout_id,
        name=layout_data.name,
        fiducials=_to_json_compatible(layout_data.fiducials),
        apertures=_to_json_compatible(layout_data.apertures),
        media_type=layout_data.media_type.value,
        created_at=layout_data.created_at or datetime.now(timezone.utc),
    )
    session.add(new_layout)
    await session.commit()
    await session.refresh(new_layout)
    return new_layout


@substrate_layout_api.get("/layouts/{layout_id}", response_model=SubstrateLayoutResponse)
async def get_layout(layout_id: str, session: AsyncSession = Depends(get_async_session)):
    """Retrieve a specific substrate layout by its unique layout_id."""
    layout = await session.scalars(
        select(SubstrateLayoutSQLModel).where(SubstrateLayoutSQLModel.layout_id == layout_id)
    )
    layout_obj = layout.one_or_none()
    if layout_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with layout_id '{layout_id}' not found",
        )
    return layout_obj


@substrate_layout_api.patch("/layouts/{layout_id}", response_model=SubstrateLayoutResponse)
async def update_layout(
    layout_id: str,
    updated_fields: SubstrateLayoutUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific substrate identified by layout_id."""
    layout = await session.scalars(
        select(SubstrateLayoutSQLModel).where(SubstrateLayoutSQLModel.layout_id == layout_id)
    )
    layout_obj = layout.one_or_none()
    if layout_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate layout with layout_id '{layout_id}' not found",
        )
    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    if "fiducials" in update_data:
        layout_obj.fiducials = _to_json_compatible(update_data.pop("fiducials"))
    if "apertures" in update_data:
        layout_obj.apertures = _to_json_compatible(update_data.pop("apertures"))
    if "media_type" in update_data:
        layout_obj.media_type = update_data.pop("media_type").value
    for field, value in update_data.items():
        setattr(layout_obj, field, value)
    layout_obj.updated_at = datetime.now(timezone.utc)
    session.add(layout_obj)
    await session.commit()
    await session.refresh(layout_obj)
    return layout_obj


@substrate_layout_api.delete("/layouts/{layout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_layout(layout_id: str, session: AsyncSession = Depends(get_async_session)):
    """Delete a specific substrate layout by its layout_id."""
    layout = await session.scalars(
        select(SubstrateLayoutSQLModel).where(SubstrateLayoutSQLModel.layout_id == layout_id)
    )
    layout_obj = layout.one_or_none()
    if layout_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate layout with layout_id '{layout_id}' not found",
        )
    substrate_count = await session.scalars(
        select(SubstrateSQLModel).where(SubstrateSQLModel.substrate_layout_id == layout_id)
    )
    if len(substrate_count.all()) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete substrate layout '{layout_id}' as it has associated substrates.",
        )
    await session.delete(layout_obj)
    await session.commit()
    return None


@substrate_layout_api.get("/layouts/{layout_id}/substrates", response_model=list[SubstrateResponse])
async def get_layout_substrates(
    layout_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve substrates with a specific layout."""
    layout = await session.scalars(
        select(SubstrateLayoutSQLModel).where(SubstrateLayoutSQLModel.layout_id == layout_id)
    )
    layout_obj = layout.one_or_none()
    if layout_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate layout with layout_id '{layout_id}' not found",
        )
    substrates = await session.scalars(
        select(SubstrateSQLModel).where(SubstrateSQLModel.substrate_layout_id == layout_id).offset(skip).limit(limit)
    )
    return substrates.all()
