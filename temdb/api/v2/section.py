from typing import List, Optional
from fastapi import APIRouter, Body, Query, HTTPException

from temdb.models.v2.section import Section, SectionCreate, SectionUpdate
from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.enum_schemas import MediaType

section_api = APIRouter(
    tags=["Sections"],
)


@section_api.get("/sections", response_model=List[Section])
async def list_sections(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    return await Section.find_all().skip(skip).limit(limit).to_list()


@section_api.get("/sections/cutting-session/{session_id}", response_model=List[Section])
async def list_cutting_session_sections(
    session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    cut_session = await CuttingSession.get(session_id)
    if not cut_session:
        raise HTTPException(status_code=404, detail="Cutting session not found")

    return (
        await Section.find(Section.cutting_session_id == cut_session.id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@section_api.get("/sections/block/{block_id}", response_model=List[Section])
async def list_block_sections(
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return (
        await Section.find({"cut_session.block.id": block_id})
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@section_api.get("/sections/specimen/{specimen_name}", response_model=List[Section])
async def list_specimen_sections(
    specimen_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    return (
        await Section.find({"cut_session.block.specimen.name": specimen_name})
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@section_api.get(
    "/sections/cutting-session/{session_id}/section/{section_id}",
    response_model=Section,
)
async def get_section(session_id: str, section_id: str):
    section = await Section.find_one(
        {"section_id": section_id, "cut_session.id": session_id}
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


@section_api.post("/sections", response_model=Section)
async def create_section(section: SectionCreate):
    cut_session = await CuttingSession.find_one(
        {"cutting_session_id": section.cutting_session_id}
    )
    if not cut_session:
        raise HTTPException(status_code=404, detail="Cutting session not found")

    new_section = Section(
        section_id=section.section_id,
        section_number=section.section_number,
        optical_image=section.optical_image,
        section_metrics=section.section_metrics,
        media_type=section.media_type,
        media_id=section.media_id,
        relative_position=section.relative_position,
        barcode=section.barcode,
        cutting_session_id=cut_session.id,
    )
    await new_section.insert()
    return new_section


@section_api.patch(
    "/sections",
    response_model=Section,
)
async def update_section(
    session_id: str,
    section_id: str,
    updated_fields: SectionUpdate = Body(...),
):
    existing_section = await Section.find_one(
        {"section_id": section_id, "cut_session.id": session_id}
    )
    if not existing_section:
        raise HTTPException(status_code=404, detail="Section not found")

    update_data = updated_fields.model_dump(exclude_unset=True)

    if update_data:
        for field, value in update_data.items():
            setattr(existing_section, field, value)

        await existing_section.save()

    return existing_section


@section_api.delete(
    "/sections/cutting-session/{session_id}/section/{section_id}", response_model=dict
)
async def delete_section(session_id: str, section_id: str):
    section = await Section.find_one(
        {"section_id": section_id, "cut_session.id": session_id}
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    await section.delete()
    return {"message": "Section deleted successfully"}


@section_api.get(
    "/sections/media/{media_type}/{media_id}", response_model=List[Section]
)
async def list_sections_by_media(
    media_type: MediaType,
    media_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    relative_position: Optional[int] = None,
):
    query = {"media_type": media_type, "media_id": media_id}
    if relative_position is not None:
        query["relative_position"] = relative_position

    return await Section.find(query).skip(skip).limit(limit).to_list()


@section_api.get("/sections/barcode/{barcode}", response_model=List[Section])
async def get_sections_by_barcode(
    barcode: str, skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    return await Section.find({"barcode": barcode}).skip(skip).limit(limit).to_list()
