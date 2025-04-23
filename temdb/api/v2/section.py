from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Body, Query, HTTPException, Depends, status
from temdb.models.v2.section import (
    Section,
    SectionCreate,
    SectionUpdate,
    SectionMetrics,
)
from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.enum_schemas import SectionQuality
from temdb.models.v2.substrate import Substrate
from temdb.models.v2.roi import ROI

section_api = APIRouter(
    tags=["Sections"],
)


@section_api.get("/sections", response_model=List[Section])
async def list_sections(
    specimen_id: Optional[str] = Query(
        None, description="Filter by human-readable Specimen ID"
    ),
    block_id: Optional[str] = Query(
        None, description="Filter by human-readable Block ID"
    ),
    cutting_session_id: Optional[str] = Query(
        None, description="Filter by human-readable Cutting Session ID"
    ),
    media_id: Optional[str] = Query(None, description="Filter by media ID"),
    quality: Optional[SectionQuality] = Query(
        None, description="Filter by section quality"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve a list of sections with optional filters and pagination."""
    query_filter = {}
    if specimen_id:
        query_filter["specimen_id"] = specimen_id
    if block_id:
        query_filter["block_id"] = block_id
    if cutting_session_id:
        query_filter["cutting_session_id"] = (
            cutting_session_id
        )
    if media_id:
        query_filter["media_id"] = media_id
    if quality:
        query_filter["section_metrics.quality"] = quality

    return (
        await Section.find(query_filter, fetch_links=True)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@section_api.get(
    "/sections/sessions/{cutting_session_id}",
    response_model=List[Section],
)
async def list_cutting_session_sections(
    cutting_session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve sections associated with a specific cutting session using its human-readable ID."""
    sections = (
        await Section.find({"cutting_session_id": cutting_session_id}, fetch_links=True)
        .sort("+section_number")
        .skip(skip)
        .limit(limit)
        .to_list()
    )
    if not sections and not await CuttingSession.find_one(
        {"cutting_session_id": cutting_session_id}
    ):
        raise HTTPException(
            status_code=404, detail=f"Cutting Session '{cutting_session_id}' not found"
        )

    return sections


@section_api.get(
    "/sections/blocks/{block_id}",
    response_model=List[Section],
)
async def list_block_sections(
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve sections associated with a specific block using its human-readable ID."""
    sections = (
        await Section.find({"block_id": block_id}, fetch_links=True)
        .sort([("cutting_session_id", 1), ("section_number", 1)])
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    return sections


@section_api.get(
    "/sections/specimens/{specimen_id}",
    response_model=List[Section],
)
async def list_specimen_sections(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve sections associated with a specific specimen using its human-readable ID."""
    sections = (
        await Section.find({"specimen_id": specimen_id}, fetch_links=True)
        .sort(
            [("block_id", 1), ("cutting_session_id", 1), ("section_number", 1)]
        )  # Sort hierarchically
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    return sections


@section_api.get(
    "/sections/sessions/{cutting_session_id}/sections/{section_id}",
    response_model=Section,
)
async def get_section(cutting_session_id: str, section_id: str):
    """Retrieve a specific section by its human-readable ID and its session's human-readable ID."""
    section = await Section.find_one(
        {"section_id": section_id, "cutting_session_id": cutting_session_id},
        fetch_links=True,
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found in session '{cutting_session_id}'",
        )
    return section


@section_api.post(
    "/sections", response_model=Section, status_code=status.HTTP_201_CREATED
)
async def create_section(section_data: SectionCreate):
    """Create a new section."""
    cut_session = await CuttingSession.find_one(
        CuttingSession.cutting_session_id == section_data.cutting_session_id,
        fetch_links=True,
    )
    if not cut_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cutting Session with ID '{section_data.cutting_session_id}' not found",
        )
    
    new_section_id = f"{section_data.media_id}_S{section_data.section_number}"

    existing_section = await Section.find_one(
        {
            "section_id": new_section_id,
            "cutting_session_ref.id": cut_session.id,
        }
    )
    if existing_section:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Section with ID '{new_section_id}' already exists in session '{section_data.cutting_session_id}'",
        )
    
    substrate = await Substrate.find_one(
        Substrate.media_id == section_data.media_id,
        fetch_links=True,
    )
    

    new_section = Section(
        section_id=new_section_id,
        section_number=section_data.section_number,
        cutting_session_id=cut_session.cutting_session_id,
        timestamp=section_data.timestamp if section_data.timestamp else datetime.now(timezone.utc),
        block_id=cut_session.block_id,
        specimen_id=cut_session.specimen_id,
        cutting_session_ref=cut_session.id,
        optical_image=section_data.optical_image,
        section_metrics=section_data.section_metrics,
        media_id=section_data.media_id,
        substrate_ref=substrate.id if substrate else None,
        barcode=section_data.barcode,
    )
    await new_section.insert()
    created_section = await Section.get(new_section.id, fetch_links=True)
    return created_section


@section_api.patch(
    "/sections/sessions/{cutting_session_id}/sections/{section_id}",
    response_model=Section,
)
async def update_section(
    cutting_session_id: str,
    section_id: str,
    updated_fields: SectionUpdate = Body(...),
):
    """Update details of a specific section."""
    section = await Section.find_one(
        {"section_id": section_id, "cutting_session_id": cutting_session_id}
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found in session '{cutting_session_id}'",
        )

    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided"
        )

    needs_save = False

    if "quality" in update_data:
        if section.section_metrics is None:
            section.section_metrics = SectionMetrics()
        section.section_metrics.quality = update_data["quality"]
        needs_save = True

    if "tissue_confidence_score" in update_data:
        if section.section_metrics is None:
            section.section_metrics = SectionMetrics()
        section.section_metrics.tissue_confidence_score = update_data[
            "tissue_confidence_score"
        ]
        needs_save = True

    for field, value in update_data.items():
        if field in ["quality", "tissue_confidence_score"]:
            continue

        if field == "section_metrics" and value is not None:
            section.section_metrics = value
            needs_save = True
        elif hasattr(section, field) and getattr(section, field) != value:
            setattr(section, field, value)
            needs_save = True

    if needs_save:
        await section.save()

    updated_section = await Section.get(section.id, fetch_links=True)
    return updated_section


@section_api.delete(
    "/sections/sessions/{cutting_session_id}/sections/{section_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_section(cutting_session_id: str, section_id: str):
    """Delete a specific section."""
    section = await Section.find_one(
        {"section_id": section_id, "cutting_session_id": cutting_session_id}
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found in session '{cutting_session_id}'",
        )

    roi_count = await ROI.find(ROI.section_ref.id == section.id).count() # Placeholder
    if roi_count > 0:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=f"Cannot delete section '{section_id}' as it has {roi_count} associated ROIs.")

    await section.delete()
    return None


@section_api.get(
    "/sections/media/{media_id}", response_model=List[Section]
)
async def list_sections_by_media(
    media_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    relative_position: Optional[int] = None,
):
    """Retrieve sections by media type and ID."""
    query = {"media_id": media_id}
    if relative_position is not None:
        query["relative_position"] = relative_position

    return await Section.find(query, fetch_links=True).skip(skip).limit(limit).to_list()


@section_api.get("/sections/barcode/{barcode}", response_model=List[Section])
async def get_sections_by_barcode(
    barcode: str, skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    """Retrieve sections by barcode."""
    return (
        await Section.find({"barcode": barcode}, fetch_links=True)
        .skip(skip)
        .limit(limit)
        .to_list()
    )
