import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import APIErrorResponse, SectionCreate, SectionQuality, SectionUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import (
    CuttingSessionSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SubstrateSQLModel,
)

section_api = APIRouter(
    tags=["Sections"],
)

logger = logging.getLogger(__name__)


def _to_section_payload(
    section: SectionSQLModel,
    *,
    cutting_session_ref_id: int | None = None,
    substrate_ref_id: int | None = None,
) -> dict:
    payload = {
        "_id": str(section.id),
        "section_id": section.section_id,
        "section_number": section.section_number,
        "timestamp": section.timestamp,
        "cutting_session_id": section.cutting_session_id,
        "block_id": section.block_id,
        "specimen_id": section.specimen_id,
        "media_id": section.media_id,
        "optical_image": section.optical_image,
        "aperture_uid": section.aperture_uid,
        "aperture_index": section.aperture_index,
        "barcode": section.barcode,
        "section_metrics": section.section_metrics,
        "created_at": section.created_at,
        "updated_at": section.updated_at,
    }
    if cutting_session_ref_id is not None:
        payload["cutting_session_ref"] = {"id": str(cutting_session_ref_id)}
    if substrate_ref_id is not None:
        payload["substrate_ref"] = {"id": str(substrate_ref_id)}
    return payload


@section_api.get("/sections")
async def list_sections(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    cutting_session_id: str | None = Query(None, description="Filter by human-readable Cutting Session ID"),
    media_id: str | None = Query(None, description="Filter by media ID"),
    quality: SectionQuality | None = Query(None, description="Filter by section quality"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of sections with optional filters and pagination."""
    statement = select(SectionSQLModel)
    if specimen_id:
        statement = statement.where(SectionSQLModel.specimen_id == specimen_id)
    if block_id:
        statement = statement.where(SectionSQLModel.block_id == block_id)
    if cutting_session_id:
        statement = statement.where(SectionSQLModel.cutting_session_id == cutting_session_id)
    if media_id:
        statement = statement.where(SectionSQLModel.media_id == media_id)
    sections = (await session.exec(statement.offset(skip).limit(limit))).all()
    if quality:
        sections = [
            section
            for section in sections
            if isinstance(section.section_metrics, dict) and section.section_metrics.get("quality") == quality.value
        ]
    return [_to_section_payload(section) for section in sections]


@section_api.get("/sections/count", response_model=int)
async def count_sections(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    cutting_session_id: str | None = Query(None, description="Filter by human-readable Cutting Session ID"),
    media_id: str | None = Query(None, description="Filter by media ID"),
    quality: SectionQuality | None = Query(None, description="Filter by section quality"),
    session: AsyncSession = Depends(get_async_session),
):
    statement = select(func.count()).select_from(SectionSQLModel)
    conditions = []
    if specimen_id:
        conditions.append(SectionSQLModel.specimen_id == specimen_id)
    if block_id:
        conditions.append(SectionSQLModel.block_id == block_id)
    if cutting_session_id:
        conditions.append(SectionSQLModel.cutting_session_id == cutting_session_id)
    if media_id:
        conditions.append(SectionSQLModel.media_id == media_id)
    if quality:
        conditions.append(SectionSQLModel.section_metrics["quality"].as_string() == quality.value)
    if conditions:
        statement = statement.where(and_(*conditions))
    return (await session.exec(statement)).one()


@section_api.get("/sections/sessions/{cutting_session_id}")
async def list_cutting_session_sections(
    cutting_session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections associated with a specific cutting session using its human-readable ID."""
    rows = (
        await session.execute(
            select(CuttingSessionSQLModel.id, SectionSQLModel)
            .select_from(CuttingSessionSQLModel)
            .outerjoin(
                SectionSQLModel,
                SectionSQLModel.cutting_session_id == CuttingSessionSQLModel.cutting_session_id,
            )
            .where(CuttingSessionSQLModel.cutting_session_id == cutting_session_id)
            .order_by(SectionSQLModel.section_number)
        )
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Cutting Session '{cutting_session_id}' not found")
    sections = [row[1] for row in rows if row[1] is not None]
    return [_to_section_payload(section) for section in sections[skip : skip + limit]]


@section_api.get("/sections/blocks/{block_id}")
async def list_block_sections(
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections associated with a specific block using its human-readable ID."""
    sections = await session.exec(
        select(SectionSQLModel)
        .where(SectionSQLModel.block_id == block_id)
        .order_by(SectionSQLModel.cutting_session_id, SectionSQLModel.section_number)
        .offset(skip)
        .limit(limit)
    )
    return [_to_section_payload(section) for section in sections.all()]


@section_api.get("/sections/specimens/{specimen_id}")
async def list_specimen_sections(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections associated with a specific specimen using its human-readable ID."""
    sections = await session.exec(
        select(SectionSQLModel)
        .where(SectionSQLModel.specimen_id == specimen_id)
        .order_by(SectionSQLModel.block_id, SectionSQLModel.cutting_session_id, SectionSQLModel.section_number)
        .offset(skip)
        .limit(limit)
    )
    return [_to_section_payload(section) for section in sections.all()]


@section_api.get("/sections/sessions/{cutting_session_id}/sections/{section_id}")
async def get_section(
    cutting_session_id: str,
    section_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a specific section by its human-readable ID and its session's human-readable ID."""
    row = (
        await session.execute(
            select(
                SectionSQLModel,
                CuttingSessionSQLModel.id,
                SubstrateSQLModel.id,
            )
            .select_from(SectionSQLModel)
            .outerjoin(
                CuttingSessionSQLModel,
                CuttingSessionSQLModel.cutting_session_id == SectionSQLModel.cutting_session_id,
            )
            .outerjoin(
                SubstrateSQLModel,
                SubstrateSQLModel.media_id == SectionSQLModel.media_id,
            )
            .where(
                SectionSQLModel.section_id == section_id,
                SectionSQLModel.cutting_session_id == cutting_session_id,
            )
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found in session '{cutting_session_id}'",
        )
    section_obj, cutting_session_ref, substrate_ref = row
    return _to_section_payload(
        section_obj,
        cutting_session_ref_id=cutting_session_ref,
        substrate_ref_id=substrate_ref,
    )


@section_api.post("/sections", status_code=status.HTTP_201_CREATED)
async def create_section(
    section_data: SectionCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new section."""
    new_section_id = f"{section_data.media_id}_S{section_data.section_number}"
    validation_row = (
        await session.execute(
            select(
                CuttingSessionSQLModel,
                SubstrateSQLModel.id,
                SectionSQLModel.id,
            )
            .select_from(CuttingSessionSQLModel)
            .outerjoin(SubstrateSQLModel, SubstrateSQLModel.media_id == section_data.media_id)
            .outerjoin(
                SectionSQLModel,
                and_(
                    SectionSQLModel.section_id == new_section_id,
                    SectionSQLModel.cutting_session_id == CuttingSessionSQLModel.cutting_session_id,
                ),
            )
            .where(CuttingSessionSQLModel.cutting_session_id == section_data.cutting_session_id)
        )
    ).first()
    cut_obj = validation_row[0] if validation_row else None
    if cut_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session with ID '{section_data.cutting_session_id}' not found",
        )
    substrate_ref = validation_row[1]
    existing_ref = validation_row[2]
    if existing_ref is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Section with ID '{new_section_id}' already exists in session '{section_data.cutting_session_id}'",
        )
    new_section = SectionSQLModel(
        section_id=new_section_id,
        section_number=section_data.section_number,
        cutting_session_id=cut_obj.cutting_session_id,
        timestamp=section_data.timestamp or datetime.now(timezone.utc),
        block_id=cut_obj.block_id,
        specimen_id=cut_obj.specimen_id,
        optical_image=section_data.optical_image,
        section_metrics=(
            section_data.section_metrics.model_dump(mode="json") if section_data.section_metrics is not None else None
        ),
        media_id=section_data.media_id,
        aperture_uid=section_data.aperture_uid,
        aperture_index=section_data.aperture_index,
        barcode=section_data.barcode,
        created_at=datetime.now(timezone.utc),
    )
    session.add(new_section)
    await session.commit()
    await session.refresh(new_section)
    return _to_section_payload(
        new_section,
        cutting_session_ref_id=cut_obj.id,
        substrate_ref_id=substrate_ref,
    )


@section_api.post(
    "/sections/batch",
    status_code=status.HTTP_201_CREATED,
    summary="Create multiple Sections in bulk",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": APIErrorResponse, "description": "Invalid input data"},
        status.HTTP_404_NOT_FOUND: {"model": APIErrorResponse, "description": "Parent resource not found"},
        status.HTTP_409_CONFLICT: {"model": APIErrorResponse, "description": "Duplicate section ID"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": APIErrorResponse, "description": "Internal server error"},
    },
)
async def create_sections_batch(
    sections_data: list[SectionCreate],
    session: AsyncSession = Depends(get_async_session),
):
    """Creates multiple Section documents from a list."""
    if not sections_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section data list cannot be empty.",
        )

    sections_to_insert: list[SectionSQLModel] = []
    session_cache: dict[str, CuttingSessionSQLModel] = {}
    substrate_cache: dict[str, SubstrateSQLModel] = {}
    seen_ids: set[str] = set()

    for idx, section_create in enumerate(sections_data):
        session_id = section_create.cutting_session_id
        media_id = section_create.media_id
        if session_id not in session_cache:
            session_result = await session.exec(
                select(CuttingSessionSQLModel).where(CuttingSessionSQLModel.cutting_session_id == session_id)
            )
            cut_session = session_result.one_or_none()
            if cut_session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"CuttingSession '{session_id}' not found for item {idx}.",
                )
            session_cache[session_id] = cut_session
        cut_session = session_cache[session_id]

        if media_id not in substrate_cache:
            substrate_result = await session.exec(
                select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id)
            )
            substrate = substrate_result.one_or_none()
            if substrate is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Substrate '{media_id}' not found for item {idx}.",
                )
            substrate_cache[media_id] = substrate

        section_id = f"{media_id}_S{section_create.section_number:05d}"
        if section_id in seen_ids:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="duplicate section IDs in batch")
        seen_ids.add(section_id)

        section_doc = SectionSQLModel(
            section_id=section_id,
            section_number=section_create.section_number,
            timestamp=section_create.timestamp or datetime.now(timezone.utc),
            cutting_session_id=cut_session.cutting_session_id,
            block_id=cut_session.block_id,
            specimen_id=cut_session.specimen_id,
            media_id=media_id,
            optical_image=section_create.optical_image,
            aperture_uid=section_create.aperture_uid,
            aperture_index=section_create.aperture_index,
            barcode=section_create.barcode,
            section_metrics=(
                section_create.section_metrics.model_dump(mode="json")
                if section_create.section_metrics is not None
                else None
            ),
            created_at=datetime.now(timezone.utc),
        )
        sections_to_insert.append(section_doc)

    session.add_all(sections_to_insert)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"duplicate sections: {error.orig}") from error
    for item in sections_to_insert:
        await session.refresh(item)
    return [_to_section_payload(item) for item in sections_to_insert]


@section_api.patch("/sections/sessions/{cutting_session_id}/sections/{section_id}")
async def update_section(
    cutting_session_id: str,
    section_id: str,
    updated_fields: SectionUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific section."""
    section = await session.exec(
        select(SectionSQLModel).where(
            SectionSQLModel.section_id == section_id,
            SectionSQLModel.cutting_session_id == cutting_session_id,
        )
    )
    section_obj = section.one_or_none()
    if section_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found in session '{cutting_session_id}'",
        )
    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    needs_save = False
    if "section_metrics" in update_data and update_data["section_metrics"] is not None:
        metrics_value = update_data["section_metrics"]
        metrics = metrics_value.model_dump(mode="json") if hasattr(metrics_value, "model_dump") else metrics_value
        if section_obj.section_metrics != metrics:
            section_obj.section_metrics = metrics
            needs_save = True
    for field in ["optical_image", "aperture_uid", "aperture_index", "barcode", "timestamp"]:
        if field in update_data and getattr(section_obj, field) != update_data[field]:
            setattr(section_obj, field, update_data[field])
            needs_save = True
    if needs_save:
        section_obj.updated_at = datetime.now(timezone.utc)
        session.add(section_obj)
        await session.commit()
        await session.refresh(section_obj)
    return _to_section_payload(section_obj)


@section_api.delete(
    "/sections/sessions/{cutting_session_id}/sections/{section_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_section(
    cutting_session_id: str,
    section_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a specific section."""
    row = (
        await session.execute(
            select(SectionSQLModel, func.count(ROISQLModel.id))
            .select_from(SectionSQLModel)
            .outerjoin(ROISQLModel, ROISQLModel.section_id == SectionSQLModel.section_id)
            .where(
                SectionSQLModel.section_id == section_id,
                SectionSQLModel.cutting_session_id == cutting_session_id,
            )
            .group_by(SectionSQLModel.id)
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found in session '{cutting_session_id}'",
        )
    section_obj, roi_count = row
    if roi_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete section '{section_id}' as it has {roi_count} associated ROIs.",
        )
    await session.delete(section_obj)
    await session.commit()
    return None


@section_api.get("/sections/media/{media_id}")
async def list_sections_by_media(
    media_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    relative_position: int | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections by media type and ID."""
    statement = select(SectionSQLModel).where(SectionSQLModel.media_id == media_id)
    if relative_position is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="relative_position is not supported")
    sections = await session.exec(statement.offset(skip).limit(limit))
    return [_to_section_payload(section) for section in sections.all()]


@section_api.get("/sections/barcode/{barcode}")
async def get_sections_by_barcode(
    barcode: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections by barcode."""
    sections = await session.exec(
        select(SectionSQLModel).where(SectionSQLModel.barcode == barcode).offset(skip).limit(limit)
    )
    return [_to_section_payload(section) for section in sections.all()]
