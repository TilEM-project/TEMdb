from typing import List, Dict
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException, Body

from temdb.models.v2.imaging_session import (
    ImagingSession,
    ImagingSessionCreate,
    ImagingSessionUpdate,
    ImagingSessionStatus,
)
from temdb.models.v2.section import Section
from temdb.models.v2.roi import ROI
from temdb.models.v2.specimen import Specimen
from temdb.models.v2.block import Block

imaging_session_api = APIRouter(
    tags=["Imaging Sessions"],
)


@imaging_session_api.get("/imaging-sessions", response_model=List[ImagingSession])
async def list_imaging_sessions(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    return await ImagingSession.find_all().skip(skip).limit(limit).to_list()


@imaging_session_api.get(
    "/imaging-sessions/{session_id}/section-rois", response_model=List[Dict]
)
async def get_imaging_session_section_rois(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    imaging_session = await ImagingSession.get(session_id)
    if not imaging_session:
        raise HTTPException(status_code=404, detail="Imaging session not found")

    pipeline = [
        {"$match": {"_id": session_id}},
        {"$unwind": "$sections"},
        {
            "$lookup": {
                "from": "rois",
                "localField": "sections.$id",
                "foreignField": "section.$id",
                "as": "section_rois",
            }
        },
        {"$project": {"section_id": "$sections.$id", "rois": "$section_rois"}},
        {"$skip": skip},
        {"$limit": limit},
    ]

    return await ImagingSession.aggregate(pipeline).to_list()


@imaging_session_api.post("/imaging-sessions", response_model=ImagingSession)
async def create_imaging_session(
    session: ImagingSessionCreate, start_time: datetime = None
):
    specimen = await Specimen.find_one(Specimen.specimen_id == session.specimen_id)
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find_one(Block.block_id == session.block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    existing_sessions = await ImagingSession.find(
        {
            "specimen_id": session.specimen_id,
            "block.id": session.block_id,
            "media_id": session.media_id,
        }
    ).to_list()
    session_number = len(existing_sessions) + 1 if existing_sessions else 0
    session_id = (
        f"{session.specimen_id}_{session.block_id}_{session.media_id}_{session_number}"
    )

    new_session = ImagingSession(
        session_id=session_id,
        specimen_id=specimen.id,
        block=block.id,
        media_type=session.media_type,
        media_id=session.media_id,
        status=ImagingSessionStatus.PLANNED,
        start_time=start_time or datetime.now(timezone.utc),
        end_time=None,
        rois=[],
    )
    await new_session.insert()
    return new_session


@imaging_session_api.get(
    "/imaging-sessions/{session_id}", response_model=ImagingSession
)
async def get_imaging_session(session_id: str):
    session = await ImagingSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Imaging session not found")
    return session


@imaging_session_api.patch(
    "/imaging-sessions/{session_id}", response_model=ImagingSession
)
async def update_imaging_session(
    session_id: str, updated_fields: ImagingSessionUpdate = Body(...)
):
    existing_session = await ImagingSession.get(session_id)
    if not existing_session:
        raise HTTPException(status_code=404, detail="Imaging session not found")

    update_data = updated_fields.model_dump(exclude_unset=True)

    if update_data:
        for field, value in update_data.items():
            setattr(existing_session, field, value)

        await existing_session.save()

    return existing_session


@imaging_session_api.delete("/imaging-sessions/{session_id}", response_model=dict)
async def delete_imaging_session(session_id: str):
    session = await ImagingSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Imaging session not found")

    await session.delete()
    return {"message": "Imaging session deleted successfully"}


@imaging_session_api.post(
    "/imaging-sessions/{session_id}/sections", response_model=ImagingSession
)
async def add_sections_to_session(
    session_id: str, section_ids: List
):
    session = await ImagingSession.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Imaging session not found")

    sections = await Section.find({"_id": {"$in": section_ids}}).to_list()
    if len(sections) != len(section_ids):
        raise HTTPException(status_code=404, detail="One or more sections not found")

    session.sections.extend(sections)
    await session.save()
    return session


@imaging_session_api.post(
    "/imaging-sessions/{session_id}/add-rois",
    response_model=ImagingSession
)
async def add_rois_to_imaging_session(
    session_id: str,
    roi_ids: List[int] = Body(...)):
    session = await ImagingSession.find_one({"session_id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Imaging session not found")
    # TODO: Check if all ROIs exist
    session.rois = roi_ids
    await session.save()
    return session


@imaging_session_api.get(
    "/imaging-sessions/specimens/{specimen_id}/imaging-sessions",
    response_model=List[ImagingSession],
)
async def get_specimen_imaging_sessions(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return (
        await ImagingSession.find(ImagingSession.specimen.id == specimen_id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@imaging_session_api.get(
    "/imaging-sessions/by-status/{status}", response_model=List[ImagingSession]
)
async def get_imaging_sessions_by_status(
    status: ImagingSessionStatus,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return (
        await ImagingSession.find(ImagingSession.status == status)
        .skip(skip)
        .limit(limit)
        .to_list()
    )
