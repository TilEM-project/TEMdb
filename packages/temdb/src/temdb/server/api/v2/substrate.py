from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import any_, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import (
    ApertureState,
    ApertureStatus,
    SectionResponse,
    SubstrateApertures,
    SubstrateCreate,
    SubstrateResponse,
    SubstrateUpdate,
)
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import SectionSQLModel, SubstrateLayoutSQLModel, SubstrateSQLModel

from ..utils import drop_null_keys, merge_extra

substrate_api = APIRouter(
    tags=["Substrates"],
)


@substrate_api.get("/substrates", response_model=list[SubstrateResponse])
async def list_substrates(
    media_type: str | None = Query(None, description="Filter by substrate media type (e.g., 'wafer', 'tape')"),
    layout_id: str | None = Query(None, description="Filter by substrate layout"),
    available: bool | None = Query(
        None, description="true: substrates with at least one available aperture; false: substrates with none"
    ),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of substrates with optional filters and pagination."""
    statement = select(SubstrateSQLModel)
    if media_type:
        statement = statement.join(SubstrateLayoutSQLModel).where(SubstrateLayoutSQLModel.media_type == media_type)
    if layout_id:
        statement = statement.where(SubstrateSQLModel.substrate_layout_id == layout_id)
    if available is not None:
        has_available = literal(ApertureStatus.AVAILABLE.value) == any_(SubstrateSQLModel.aperture_status)
        statement = statement.where(has_available if available else ~has_available)
    substrates = (await session.scalars(statement.order_by(SubstrateSQLModel.media_id).offset(skip).limit(limit))).all()
    return substrates


@substrate_api.post("/substrates", status_code=status.HTTP_201_CREATED, response_model=SubstrateResponse)
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
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Substrate with media_id '{substrate_data.media_id}' already exists.",
        )
    layout = await session.get(SubstrateLayoutSQLModel, substrate_data.substrate_layout_id)
    if layout is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate layout '{substrate_data.substrate_layout_id}' not found",
        )
    aperture_count = len(layout.apertures or [])
    aperture_status = substrate_data.aperture_status or ["available"] * aperture_count
    if len(aperture_status) != aperture_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"aperture_status has {len(aperture_status)} entries; layout '{layout.layout_id}' has "
            f"{aperture_count} apertures",
        )
    new_substrate = SubstrateSQLModel(
        media_id=substrate_data.media_id,
        substrate_layout_id=substrate_data.substrate_layout_id,
        aperture_status=[str(getattr(value, "value", value)) for value in aperture_status],
        created_at=substrate_data.created_at or datetime.now(timezone.utc),
        extra=drop_null_keys(substrate_data.extra),
    )
    session.add(new_substrate)
    await session.commit()
    await session.refresh(new_substrate)
    return new_substrate


@substrate_api.get("/substrates/{media_id}", response_model=SubstrateResponse)
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
async def update_substrate(
    media_id: str,
    updated_fields: SubstrateUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific substrate identified by media_id."""
    substrate = await session.scalars(
        select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id).with_for_update()
    )
    substrate_obj = substrate.one_or_none()
    if substrate_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    update_data = updated_fields.model_dump(
        exclude_unset=True,
    )
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    extra_changes = update_data.pop("extra", None)
    if "substrate_layout_id" in update_data:
        layout = await session.get(SubstrateLayoutSQLModel, update_data["substrate_layout_id"])
        if layout is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Substrate layout '{update_data['substrate_layout_id']}' not found",
            )
        if len(layout.apertures or []) != len(substrate_obj.aperture_status):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Layout '{layout.layout_id}' has {len(layout.apertures or [])} apertures; substrate "
                f"'{media_id}' has {len(substrate_obj.aperture_status)}",
            )
    changed_statuses = update_data.pop("aperture_status", None) or {}
    unknown = sorted(index for index in changed_statuses if not 0 <= index < len(substrate_obj.aperture_status))
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Substrate '{media_id}' has no apertures {unknown}",
        )
    if changed_statuses:
        statuses = list(substrate_obj.aperture_status)
        for index, value in changed_statuses.items():
            statuses[index] = value.value
        substrate_obj.aperture_status = statuses
    for field, value in update_data.items():
        setattr(substrate_obj, field, value)
    if extra_changes is not None:
        substrate_obj.extra = merge_extra(SubstrateSQLModel.extra, extra_changes)
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
    await session.delete(substrate_obj)
    await session.commit()
    return None


@substrate_api.get("/substrates/{media_id}/sections", response_model=list[SectionResponse])
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
        .order_by(SectionSQLModel.section_number, SectionSQLModel.id)
        .offset(skip)
        .limit(limit)
    )
    return sections.all()


@substrate_api.get("/substrates/{media_id}/apertures", response_model=SubstrateApertures)
async def get_substrate_apertures(media_id: str, session: AsyncSession = Depends(get_async_session)):
    """A substrate's layout with each aperture's shape, status and sections."""
    row = (
        await session.execute(
            select(SubstrateSQLModel, SubstrateLayoutSQLModel)
            .join(SubstrateLayoutSQLModel)
            .where(SubstrateSQLModel.media_id == media_id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    substrate_obj, layout_obj = row
    placed = await session.execute(
        select(SectionSQLModel.aperture_index, SectionSQLModel.section_id)
        .where(SectionSQLModel.media_id == media_id)
        .order_by(SectionSQLModel.section_number, SectionSQLModel.id)
    )
    sections_by_aperture: dict[int | None, list[str]] = {}
    for aperture_index, section_id in placed:
        sections_by_aperture.setdefault(aperture_index, []).append(section_id)
    return SubstrateApertures(
        media_id=media_id,
        layout=layout_obj,
        apertures=[
            ApertureState(
                index=index, shape=shape, status=aperture_status, sections=sections_by_aperture.get(index, [])
            )
            for index, (shape, aperture_status) in enumerate(
                zip(layout_obj.apertures or [], substrate_obj.aperture_status, strict=True)
            )
        ],
        blank_sections=sections_by_aperture.get(None, []),
    )
