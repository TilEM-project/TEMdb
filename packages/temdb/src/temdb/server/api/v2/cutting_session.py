from fastapi import APIRouter, Body, HTTPException, Query, status

from temdb.models import CuttingSessionCreate, CuttingSessionUpdate
from temdb.server.documents import (
    BlockDocument as Block,
)
from temdb.server.documents import (
    CuttingSessionDocument as CuttingSession,
)
from temdb.server.documents import (
    SectionDocument as Section,
)
from temdb.server.responses.cutting_session import CuttingSessionRead

cutting_session_api = APIRouter(
    tags=["Cutting Sessions"],
)


@cutting_session_api.get("/cutting-sessions", response_model=list[CuttingSessionRead])
async def list_cutting_sessions(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    operator: str | None = Query(None, description="Filter by operator name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve a list of cutting sessions with optional filters and pagination."""
    query_filter: dict = {}
    if specimen_id:
        query_filter["specimen_id"] = specimen_id
    if block_id:
        query_filter["block_id"] = block_id
    if operator:
        query_filter["operator"] = operator

    sessions = await CuttingSession.find(query_filter).skip(skip).limit(limit).to_list()
    return [CuttingSessionRead.from_doc(s) for s in sessions]


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions/{cutting_session_id}/sections",
    response_model=list[Section],
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

    return (
        await Section.find(Section.cutting_session_ref == cutting_session.id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@cutting_session_api.post(
    "/cutting-sessions",
    response_model=CuttingSessionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_cutting_session(session_data: CuttingSessionCreate):
    """Create a new cutting session."""
    if await CuttingSession.find_one({"cutting_session_id": session_data.cutting_session_id}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cutting Session with ID '{session_data.cutting_session_id}' already exists",
        )

    block = await Block.find_one(Block.block_id == session_data.block_id)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{session_data.block_id}' not found",
        )

    new_session = CuttingSession(
        cutting_session_id=session_data.cutting_session_id,
        block_id=block.block_id,
        specimen_id=block.specimen_id,
        block_ref=block.id,
        specimen_ref=block.specimen_ref,
        start_time=session_data.start_time,
        end_time=session_data.end_time,
        operator=session_data.operator,
        sectioning_device=session_data.sectioning_device,
        media_type=session_data.media_type,
    )
    await new_session.insert()
    return CuttingSessionRead.from_doc(new_session)


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions/{cutting_session_id}",
    response_model=CuttingSessionRead,
)
async def get_cutting_session(specimen_id: str, block_id: str, cutting_session_id: str):
    """Retrieve a specific cutting session by its human-readable ID."""
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
    return CuttingSessionRead.from_doc(cutting_session)


@cutting_session_api.patch("/cutting-sessions/{cutting_session_id}", response_model=CuttingSessionRead)
async def update_cutting_session(cutting_session_id: str, updated_fields: CuttingSessionUpdate = Body(...)):
    """Update details of a specific cutting session."""
    session = await CuttingSession.find_one({"cutting_session_id": cutting_session_id})
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session with ID '{cutting_session_id}' not found",
        )

    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    needs_save = False
    for field, value in update_data.items():
        if hasattr(session, field) and getattr(session, field) != value:
            setattr(session, field, value)
            needs_save = True

    if needs_save:
        await session.save()

    return CuttingSessionRead.from_doc(session)


@cutting_session_api.delete("/cutting-sessions/{cutting_session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cutting_session(cutting_session_id: str):
    """Delete a specific cutting session."""
    session = await CuttingSession.find_one({"cutting_session_id": cutting_session_id})
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session with ID '{cutting_session_id}' not found",
        )

    section_count = await Section.find(Section.cutting_session_ref == session.id).count()
    if section_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete session '{cutting_session_id}' as it has {section_count} associated sections.",
        )

    await session.delete()
    return None


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/sessions",
    response_model=list[CuttingSessionRead],
)
async def list_block_cutting_sessions(
    specimen_id: str,
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve cutting sessions associated with a specific block using human-readable IDs."""
    sessions = (
        await CuttingSession.find({"block_id": block_id, "specimen_id": specimen_id})
        .skip(skip)
        .limit(limit)
        .to_list()
    )
    return [CuttingSessionRead.from_doc(s) for s in sessions]
