from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import SectionResponse, SubstrateCreate, SubstrateResponse, SubstrateUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import SectionSQLModel, SubstrateSQLModel

from ..utils import include_extra

substrate_api = APIRouter(
    tags=["Substrates"],
)


def _to_json_compatible(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return jsonable_encoder(value)


@substrate_api.get("/substrates", response_model=list[SubstrateResponse])
@include_extra
async def list_substrates(
    media_type: str | None = Query(None, description="Filter by substrate media type (e.g., 'wafer', 'tape')"),
    status: str | None = Query(None, description="Filter by substrate status (e.g., 'new', 'used')"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of substrates with optional filters and pagination."""
    statement = select(SubstrateSQLModel)
    if media_type:
        statement = statement.where(SubstrateSQLModel.media_type == media_type)
    if status:
        statement = statement.where(SubstrateSQLModel.status == status)
    substrates = (await session.scalars(statement.offset(skip).limit(limit))).all()
    return substrates


@substrate_api.post("/substrates", status_code=status.HTTP_201_CREATED, response_model=SubstrateResponse)
@include_extra
async def create_substrate(
    substrate_data: SubstrateCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new substrate."""
    existing_substrate = await session.scalars(
        select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == substrate_data.media_id)
    )
    if existing_substrate.one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Substrate with media_id '{substrate_data.media_id}' already exists.",
        )
    new_substrate = SubstrateSQLModel(
        media_id=substrate_data.media_id,
        media_type=substrate_data.media_type,
        uid=substrate_data.uid,
        status=substrate_data.status,
        refpoint=(
            substrate_data.refpoint.model_dump(mode="json")
            if getattr(substrate_data, "refpoint", None) is not None
            else None
        ),
        refpoint_world=(
            substrate_data.refpoint_world.model_dump(mode="json")
            if getattr(substrate_data, "refpoint_world", None) is not None
            else None
        ),
        source_path=str(substrate_data.source_path) if substrate_data.source_path is not None else None,
        metadata_json=(
            substrate_data.metadata.model_dump(mode="json")
            if getattr(substrate_data, "metadata", None) is not None
            else None
        ),
        apertures=(
            [ap.model_dump(mode="json") for ap in substrate_data.apertures]
            if getattr(substrate_data, "apertures", None) is not None
            else None
        ),
        created_at=substrate_data.created_at or datetime.now(timezone.utc),
        extra=substrate_data.model_extra,
    )
    session.add(new_substrate)
    await session.commit()
    await session.refresh(new_substrate)
    return new_substrate


@substrate_api.get("/substrates/{media_id}", response_model=SubstrateResponse)
@include_extra
async def get_substrate(media_id: str, session: AsyncSession = Depends(get_async_session)):
    """Retrieve a specific substrate by its unique media_id."""
    substrate = await session.scalars(select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id))
    substrate_obj = substrate.one_or_none()
    if substrate_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    return substrate_obj


@substrate_api.patch("/substrates/{media_id}", response_model=SubstrateResponse)
@include_extra
async def update_substrate(
    media_id: str,
    updated_fields: SubstrateUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific substrate identified by media_id."""
    substrate = await session.scalars(select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id))
    substrate_obj = substrate.one_or_none()
    if substrate_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    update_data = updated_fields.model_dump(
        exclude_unset=True,
        extra=False,
    )
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    if "metadata" in update_data:
        substrate_obj.metadata_json = _to_json_compatible(update_data.pop("metadata"))
    for field in ("refpoint", "refpoint_world", "apertures"):
        if field in update_data:
            update_data[field] = _to_json_compatible(update_data[field])
    if update_data.get("source_path") is not None:
        update_data["source_path"] = str(update_data["source_path"])  # URI.Type -> String column
    for field, value in update_data.items():
        setattr(substrate_obj, field, value)
    if updated_fields.model_extra:
        substrate_obj.extra = {**(substrate_obj.extra or {}), **updated_fields.model_extra}
    substrate_obj.updated_at = datetime.now(timezone.utc)
    session.add(substrate_obj)
    await session.commit()
    await session.refresh(substrate_obj)
    return substrate_obj


@substrate_api.delete("/substrates/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_substrate(media_id: str, session: AsyncSession = Depends(get_async_session)):
    """Delete a specific substrate by its media_id."""
    substrate = await session.scalars(select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id))
    substrate_obj = substrate.one_or_none()
    if substrate_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    section_count = await session.scalars(select(SectionSQLModel).where(SectionSQLModel.media_id == media_id))
    if len(section_count.all()) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete substrate '{media_id}' as it has associated sections.",
        )
    await session.delete(substrate_obj)
    await session.commit()
    return None


@substrate_api.get("/substrates/{media_id}/sections", response_model=list[SectionResponse])
@include_extra
async def get_substrate_sections(
    media_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections associated with a specific substrate, identified by media_id."""
    substrate = await session.scalars(select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id))
    substrate_obj = substrate.one_or_none()
    if substrate_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    sections = await session.scalars(
        select(SectionSQLModel)
        .where(SectionSQLModel.media_id == media_id)
        .order_by(SectionSQLModel.section_number)
        .offset(skip)
        .limit(limit)
    )
    return sections.all()
