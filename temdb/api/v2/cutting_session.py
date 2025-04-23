from typing import List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, status

from temdb.models.v2.block import Block
from temdb.models.v2.cutting_session import (
    CuttingSession,
    CuttingSessionCreate,
    CuttingSessionUpdate,
)
from temdb.models.v2.section import Section

cutting_session_api = APIRouter(
    tags=["Cutting Sessions"],
)


@cutting_session_api.get("/cutting-sessions", response_model=List[CuttingSession])
async def list_cutting_sessions(
    specimen_id: Optional[str] = Query(
        None, description="Filter by human-readable Specimen ID"
    ),
    block_id: Optional[str] = Query(
        None, description="Filter by human-readable Block ID"
    ),
    operator: Optional[str] = Query(None, description="Filter by operator name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve a list of cutting sessions with optional filters and pagination."""
    query_filter = {}
    if specimen_id:
        query_filter["specimen_id"] = specimen_id
    if block_id:
        query_filter["block_id"] = block_id
    if operator:
        query_filter["operator"] = operator

    return (
        await CuttingSession.find(query_filter, fetch_links=True)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions/{cutting_session_id}/sections",
    response_model=List[Section],
)
async def get_cutting_session_sections(
    specimen_id: str, 
    block_id: str, 
    cutting_session_id: str, 
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve sections associated with a specific cutting session."""
    cutting_session = await CuttingSession.find_one(
        {
            "cutting_session_id": cutting_session_id,
            "block_id": block_id,
            "specimen_id": specimen_id,
        }
    )
    if not cutting_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session '{cutting_session_id}' not found or does not match specimen/block.",
        )

    sections = (
        await Section.find(
            Section.cutting_session_ref.id
            == cutting_session.id,
            fetch_links=True,
        )
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    return sections


@cutting_session_api.post(
    "/cutting-sessions",
    response_model=CuttingSession,
    status_code=status.HTTP_201_CREATED,
)
async def create_cutting_session(session_data: CuttingSessionCreate):
    """Create a new cutting session."""
    if await CuttingSession.find_one(
        {"cutting_session_id": session_data.cutting_session_id}
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cutting Session with ID '{session_data.cutting_session_id}' already exists",
        )

    block = await Block.find_one(
        Block.block_id == session_data.block_id, fetch_links=True
    )
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{session_data.block_id}' not found",
        )

    if not block.specimen_ref:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Block '{block.block_id}' is missing its specimen reference.",
        )

    new_session = CuttingSession(
        cutting_session_id=session_data.cutting_session_id,
        block_id=block.block_id,
        specimen_id=block.specimen_id,
        block_ref=block.id,
        specimen_ref=block.specimen_ref.id,
        start_time=session_data.start_time,
        end_time=session_data.end_time,
        operator=session_data.operator,
        sectioning_device=session_data.sectioning_device,
        media_type=session_data.media_type,
    )
    await new_session.insert()
    created_session = await CuttingSession.get(new_session.id, fetch_links=True)
    return created_session


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions/{cutting_session_id}",
    response_model=CuttingSession,
)
async def get_cutting_session(specimen_id: str, block_id: str, cutting_session_id: str):
    """Retrieve a specific cutting session by its human-readable ID, ensuring it matches specimen/block context."""
    cutting_session = await CuttingSession.find_one(
        {
            "cutting_session_id": cutting_session_id,
            "block_id": block_id,
            "specimen_id": specimen_id,
        },
        fetch_links=True,
    )
    if not cutting_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session '{cutting_session_id}' not found or does not match specimen/block.",
        )
    return cutting_session


@cutting_session_api.patch(
    "/cutting-sessions/{cutting_session_id}", response_model=CuttingSession
)
async def update_cutting_session(
    cutting_session_id: str, updated_fields: CuttingSessionUpdate = Body(...)
):
    """Update details of a specific cutting session."""
    session = await CuttingSession.find_one({"cutting_session_id": cutting_session_id})
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session with ID '{cutting_session_id}' not found",
        )

    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided"
        )

    needs_save = False
    for field, value in update_data.items():
        if hasattr(session, field) and getattr(session, field) != value:
            setattr(session, field, value)
            needs_save = True

    if needs_save:
        await session.save()

    updated_session = await CuttingSession.get(session.id, fetch_links=True)
    return updated_session


@cutting_session_api.delete(
    "/cutting-sessions/{cutting_session_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_cutting_session(cutting_session_id: str):
    """Delete a specific cutting session."""
    session = await CuttingSession.find_one({"cutting_session_id": cutting_session_id})
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session with ID '{cutting_session_id}' not found",
        )


    section_count = await Section.find(
        Section.cutting_session_ref.id == session.id
    ).count()
    if section_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete session '{cutting_session_id}' as it has {section_count} associated sections.",
        )

    await session.delete()
    return None


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions",
    response_model=List[CuttingSession],
)
async def list_block_cutting_sessions(
    specimen_id: str,
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve cutting sessions associated with a specific block using human-readable IDs."""
    sessions = (
        await CuttingSession.find(
            {"block_id": block_id, "specimen_id": specimen_id}, fetch_links=True
        )
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    return sessions
