from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import CuttingSessionCreate, CuttingSessionUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import BlockSQLModel, CuttingSessionSQLModel, SectionSQLModel, SpecimenSQLModel

cutting_session_api = APIRouter(
    tags=["Cutting Sessions"],
)


def _sql_cutting_session_payload(
    session: CuttingSessionSQLModel,
    block_internal_id: int | None = None,
    specimen_internal_id: int | None = None,
) -> dict:
    payload = {
        "_id": str(session.id),
        "cutting_session_id": session.cutting_session_id,
        "specimen_id": session.specimen_id,
        "block_id": session.block_id,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "operator": session.operator,
        "sectioning_device": session.sectioning_device,
        "media_type": session.media_type,
        "knife_id": session.knife_id,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
    if block_internal_id is not None:
        payload["block_ref"] = {"id": str(block_internal_id)}
    if specimen_internal_id is not None:
        payload["specimen_ref"] = {"id": str(specimen_internal_id)}
    return payload


def _sql_section_payload(section: SectionSQLModel, cutting_session_internal_id: int | None = None) -> dict:
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
    if cutting_session_internal_id is not None:
        payload["cutting_session_ref"] = {"id": str(cutting_session_internal_id)}
    return payload


@cutting_session_api.get("/cutting-sessions")
async def list_cutting_sessions(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    operator: str | None = Query(None, description="Filter by operator name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of cutting sessions with optional filters and pagination."""
    statement = select(CuttingSessionSQLModel)
    if specimen_id:
        statement = statement.where(CuttingSessionSQLModel.specimen_id == specimen_id)
    if block_id:
        statement = statement.where(CuttingSessionSQLModel.block_id == block_id)
    if operator:
        statement = statement.where(CuttingSessionSQLModel.operator == operator)
    sessions = (await session.exec(statement.offset(skip).limit(limit))).all()
    return [_sql_cutting_session_payload(c) for c in sessions]


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions/{cutting_session_id}/sections",
)
async def get_cutting_session_sections(
    specimen_id: str,
    block_id: str,
    cutting_session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections associated with a specific cutting session."""
    cutting_session = await session.exec(
        select(CuttingSessionSQLModel).where(
            CuttingSessionSQLModel.cutting_session_id == cutting_session_id,
            CuttingSessionSQLModel.block_id == block_id,
            CuttingSessionSQLModel.specimen_id == specimen_id,
        )
    )
    cutting_session_obj = cutting_session.one_or_none()
    if cutting_session_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session '{cutting_session_id}' not found or does not match specimen/block.",
        )
    sections = await session.exec(
        select(SectionSQLModel)
        .where(SectionSQLModel.cutting_session_id == cutting_session_id)
        .offset(skip)
        .limit(limit)
    )
    return [_sql_section_payload(s, cutting_session_obj.id) for s in sections.all()]


@cutting_session_api.post(
    "/cutting-sessions",
    status_code=status.HTTP_201_CREATED,
)
async def create_cutting_session(
    session_data: CuttingSessionCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new cutting session."""
    existing = await session.exec(
        select(CuttingSessionSQLModel).where(
            CuttingSessionSQLModel.cutting_session_id == session_data.cutting_session_id
        )
    )
    if existing.one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cutting Session with ID '{session_data.cutting_session_id}' already exists",
        )
    block_row = (
        await session.execute(
            select(BlockSQLModel, SpecimenSQLModel.id)
            .select_from(BlockSQLModel)
            .outerjoin(SpecimenSQLModel, SpecimenSQLModel.specimen_id == BlockSQLModel.specimen_id)
            .where(BlockSQLModel.block_id == session_data.block_id)
        )
    ).first()
    block_obj = block_row[0] if block_row else None
    if block_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{session_data.block_id}' not found",
        )
    new_session = CuttingSessionSQLModel(
        cutting_session_id=session_data.cutting_session_id,
        block_id=block_obj.block_id,
        specimen_id=block_obj.specimen_id,
        start_time=session_data.start_time,
        end_time=session_data.end_time,
        operator=session_data.operator,
        sectioning_device=session_data.sectioning_device,
        media_type=session_data.media_type,
        knife_id=session_data.knife_id,
        created_at=datetime.now(timezone.utc),
    )
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)
    specimen_ref = block_row[1]
    payload = _sql_cutting_session_payload(new_session, block_obj.id, specimen_ref)
    return payload


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions/{cutting_session_id}",
)
async def get_cutting_session(
    specimen_id: str,
    block_id: str,
    cutting_session_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a specific cutting session by its human-readable ID, ensuring it matches specimen/block context."""
    row = (
        await session.execute(
            select(
                CuttingSessionSQLModel,
                BlockSQLModel.id,
                SpecimenSQLModel.id,
            )
            .select_from(CuttingSessionSQLModel)
            .outerjoin(
                BlockSQLModel,
                and_(
                    BlockSQLModel.block_id == CuttingSessionSQLModel.block_id,
                    BlockSQLModel.specimen_id == CuttingSessionSQLModel.specimen_id,
                ),
            )
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == CuttingSessionSQLModel.specimen_id,
            )
            .where(
                CuttingSessionSQLModel.cutting_session_id == cutting_session_id,
                CuttingSessionSQLModel.block_id == block_id,
                CuttingSessionSQLModel.specimen_id == specimen_id,
            )
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session '{cutting_session_id}' not found or does not match specimen/block.",
        )
    cutting_session_obj, block_ref, specimen_ref = row
    return _sql_cutting_session_payload(
        cutting_session_obj,
        block_ref,
        specimen_ref,
    )


@cutting_session_api.patch("/cutting-sessions/{cutting_session_id}")
async def update_cutting_session(
    cutting_session_id: str,
    updated_fields: CuttingSessionUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific cutting session."""
    cutting_session = await session.exec(
        select(CuttingSessionSQLModel).where(CuttingSessionSQLModel.cutting_session_id == cutting_session_id)
    )
    cutting_session_obj = cutting_session.one_or_none()
    if cutting_session_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session with ID '{cutting_session_id}' not found",
        )
    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    changed = False
    for field, value in update_data.items():
        if hasattr(cutting_session_obj, field) and getattr(cutting_session_obj, field) != value:
            setattr(cutting_session_obj, field, value)
            changed = True
    if changed:
        cutting_session_obj.updated_at = datetime.now(timezone.utc)
        session.add(cutting_session_obj)
        await session.commit()
        await session.refresh(cutting_session_obj)
    return _sql_cutting_session_payload(cutting_session_obj)


@cutting_session_api.delete("/cutting-sessions/{cutting_session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cutting_session(
    cutting_session_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a specific cutting session."""
    cutting_session = await session.exec(
        select(CuttingSessionSQLModel).where(CuttingSessionSQLModel.cutting_session_id == cutting_session_id)
    )
    cutting_session_obj = cutting_session.one_or_none()
    if cutting_session_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session with ID '{cutting_session_id}' not found",
        )
    sections = await session.exec(
        select(SectionSQLModel).where(SectionSQLModel.cutting_session_id == cutting_session_id)
    )
    if sections.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete session '{cutting_session_id}' as it has associated sections.",
        )
    await session.delete(cutting_session_obj)
    await session.commit()
    return None


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions",
)
async def list_block_cutting_sessions(
    specimen_id: str,
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve cutting sessions associated with a specific block using human-readable IDs."""
    rows = (
        await session.execute(
            select(
                CuttingSessionSQLModel,
                BlockSQLModel.id,
                SpecimenSQLModel.id,
            )
            .select_from(CuttingSessionSQLModel)
            .outerjoin(
                BlockSQLModel,
                and_(
                    BlockSQLModel.block_id == CuttingSessionSQLModel.block_id,
                    BlockSQLModel.specimen_id == CuttingSessionSQLModel.specimen_id,
                ),
            )
            .outerjoin(
                SpecimenSQLModel,
                SpecimenSQLModel.specimen_id == CuttingSessionSQLModel.specimen_id,
            )
            .where(
                CuttingSessionSQLModel.block_id == block_id,
                CuttingSessionSQLModel.specimen_id == specimen_id,
            )
            .offset(skip)
            .limit(limit)
        )
    ).all()
    return [
        _sql_cutting_session_payload(
            s,
            block_ref,
            specimen_ref,
        )
        for s, block_ref, specimen_ref in rows
    ]
