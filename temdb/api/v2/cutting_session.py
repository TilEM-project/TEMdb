from typing import List

from beanie import PydanticObjectId
from fastapi import APIRouter, Body, HTTPException, Query

from temdb.models.v2.specimen import Specimen
from temdb.models.v2.block import Block
from temdb.models.v2.section import Section
from temdb.models.v2.cutting_session import (
    CuttingSession,
    CuttingSessionCreate,
    CuttingSessionUpdate,
)

cutting_session_api = APIRouter(
    tags=["Cutting Sessions"],
)


@cutting_session_api.get("/cutting-sessions", response_model=List[CuttingSession])
async def list_cutting_sessions(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    return await CuttingSession.find_all().skip(skip).limit(limit).to_list()


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_name}/blocks/{block_id}/cutting-sessions/{session_id}/sections",
    response_model=List[Section],
)
async def get_cutting_session_sections(
    specimen_name: str,
    block_id: str,
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find_one({"specimen.id": specimen.id, "block_id": block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    cutting_session = await CuttingSession.find_one(
        {"block.id": block.id, "session_id": session_id}
    )
    if not cutting_session:
        raise HTTPException(status_code=404, detail="Cutting session not found")

    return (
        await Section.find(Section.cutting_session_id == cutting_session.id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@cutting_session_api.post("/cutting-sessions", response_model=CuttingSession)
async def create_cutting_session(session: CuttingSessionCreate):
    block = await Block.find_one({"block_id": session.block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    new_session = CuttingSession(
        cutting_session_id=session.cutting_session_id,
        start_time=session.start_time,
        end_time=session.end_time,
        operator=session.operator,
        sectioning_device=session.sectioning_device,
        media_type=session.media_type,
        specimen_id=block.specimen_id,
        block_id=block.id,
    )
    await new_session.insert()
    return new_session


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/cutting-sessions/{cutting_session_id}",
    response_model=CuttingSession,
)
async def get_cutting_session(specimen_id: str, block_id: str, cutting_session_id: str):
    specimen = await Specimen.find_one({"specimen_id": specimen_id})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find_one({"specimen_id": specimen.id, "block_id": block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    cutting_session = await CuttingSession.find_one(
        {"block_id": block.id, "cutting_session_id": cutting_session_id}
    )
    if not cutting_session:
        raise HTTPException(status_code=404, detail="Cutting session not found")
    return cutting_session


@cutting_session_api.patch(
    "/cutting-sessions/{cutting_session_id}", response_model=CuttingSession
)
async def update_cutting_session(
    cutting_session_id: PydanticObjectId, updated_fields: CuttingSessionUpdate = Body(...)
):
    existing_session = await CuttingSession.get(cutting_session_id)
    if not existing_session:
        raise HTTPException(status_code=404, detail="Cutting session not found")

    update_data = updated_fields.model_dump(exclude_unset=True)

    if update_data:
        for field, value in update_data.items():
            setattr(existing_session, field, value)

        await existing_session.save()

    return existing_session


@cutting_session_api.delete("/cutting-sessions/{cutting_session_id}", response_model=dict)
async def delete_cutting_session(cutting_session_id: str):
    session = await CuttingSession.get(cutting_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Cutting session not found")

    await session.delete()
    return {"message": "Cutting session deleted successfully"}


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks/{block_id}/cutting-sessions",
    response_model=List[CuttingSession],
)
async def list_block_cutting_sessions(
    specimen_id: str,
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    specimen = await Specimen.find_one({"specimen_id": specimen_id})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find_one({"specimen_id": specimen.id, "block_id": block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    return (
        await CuttingSession.find(CuttingSession.block_id == block.id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@cutting_session_api.get(
    "/cutting-sessions/specimens/{specimen_id}/blocks", response_model=List[Block]
)
async def list_specimen_blocks(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    specimen = await Specimen.find_one({"specimen_id": specimen_id})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    return (
        await Block.find(Block.specimen_id == specimen.id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )
