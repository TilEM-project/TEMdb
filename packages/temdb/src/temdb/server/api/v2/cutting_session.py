from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import CuttingSessionCreate, CuttingSessionResponse, CuttingSessionUpdate, SectionResponse
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import BlockSQLModel, CuttingSessionSQLModel, SectionSQLModel

cutting_session_api = APIRouter(
    tags=["Cutting Sessions"],
)


@cutting_session_api.get("/cutting-sessions", response_model=list[CuttingSessionResponse])
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
    return sessions


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions/{cutting_session_id}/sections",
    response_model=list[SectionResponse],
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
    return sections.all()


@cutting_session_api.post(
    "/cutting-sessions",
    status_code=status.HTTP_201_CREATED,
    response_model=CuttingSessionResponse,
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
    block_obj = (
        await session.execute(select(BlockSQLModel).where(BlockSQLModel.block_id == session_data.block_id))
    ).scalar_one_or_none()
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
        created_at=session_data.created_at or datetime.now(timezone.utc),
    )
    session.add(new_session)
    await session.commit()
    await session.refresh(new_session)
    return new_session


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions/{cutting_session_id}",
    response_model=CuttingSessionResponse,
)
async def get_cutting_session(
    specimen_id: str,
    block_id: str,
    cutting_session_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a specific cutting session by its human-readable ID, ensuring it matches specimen/block context."""
    cutting_session_obj = (
        await session.execute(
            select(CuttingSessionSQLModel).where(
                CuttingSessionSQLModel.cutting_session_id == cutting_session_id,
                CuttingSessionSQLModel.block_id == block_id,
                CuttingSessionSQLModel.specimen_id == specimen_id,
            )
        )
    ).scalar_one_or_none()
    if cutting_session_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session '{cutting_session_id}' not found or does not match specimen/block.",
        )
    return cutting_session_obj


@cutting_session_api.patch("/cutting-sessions/{cutting_session_id}", response_model=CuttingSessionResponse)
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
    for field, value in update_data.items():
        setattr(cutting_session_obj, field, value)
    cutting_session_obj.updated_at = datetime.now(timezone.utc)
    session.add(cutting_session_obj)
    await session.commit()
    await session.refresh(cutting_session_obj)
    return cutting_session_obj


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
    response_model=list[CuttingSessionResponse],
)
async def list_block_cutting_sessions(
    specimen_id: str,
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve cutting sessions associated with a specific block using human-readable IDs."""
    sessions = (
        (
            await session.execute(
                select(CuttingSessionSQLModel)
                .where(
                    CuttingSessionSQLModel.block_id == block_id,
                    CuttingSessionSQLModel.specimen_id == specimen_id,
                )
                .offset(skip)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return sessions
