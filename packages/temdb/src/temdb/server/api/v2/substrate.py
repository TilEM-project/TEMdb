from datetime import datetime, timezone

from fastapi import APIRouter, Body, HTTPException, Query, status
from temdb.models import SubstrateCreate, SubstrateUpdate
from temdb.server.documents import (
    SectionDocument as Section,
)
from temdb.server.documents import (
    SubstrateDocument as Substrate,
)

substrate_api = APIRouter(
    tags=["Substrates"],
)


@substrate_api.get("/substrates", response_model=list[Substrate])
async def list_substrates(
    media_type: str | None = Query(None, description="Filter by substrate media type (e.g., 'wafer', 'tape')"),
    status: str | None = Query(None, description="Filter by substrate status (e.g., 'new', 'used')"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
):
    """Retrieve a list of substrates with optional filters and pagination."""
    query_filter = {}
    if media_type:
        query_filter["media_type"] = media_type
    if status:
        query_filter["status"] = status

    substrates = await Substrate.find(query_filter, fetch_links=False).skip(skip).limit(limit).to_list()
    return substrates


@substrate_api.post("/substrates", response_model=Substrate, status_code=status.HTTP_201_CREATED)
async def create_substrate(substrate_data: SubstrateCreate):
    """Create a new substrate."""
    existing_substrate = await Substrate.find_one({"media_id": substrate_data.media_id})
    if existing_substrate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Substrate with media_id '{substrate_data.media_id}' already exists.",
        )

    new_substrate = Substrate(
        **substrate_data.model_dump(exclude_unset=True),
        created_at=datetime.now(timezone.utc),
        updated_at=None,
    )

    await new_substrate.insert()

    created_substrate = await Substrate.get(new_substrate.id)
    if not created_substrate:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve created substrate after insertion.",
        )
    return created_substrate


@substrate_api.get("/substrates/{media_id}", response_model=Substrate)
async def get_substrate(media_id: str):
    """Retrieve a specific substrate by its unique media_id."""
    substrate = await Substrate.find_one(Substrate.media_id == media_id)
    if not substrate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    return substrate


@substrate_api.patch("/substrates/{media_id}", response_model=Substrate)
async def update_substrate(media_id: str, updated_fields: SubstrateUpdate = Body(...)):
    """Update details of a specific substrate identified by media_id."""
    substrate = await Substrate.find_one(Substrate.media_id == media_id)
    if not substrate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )

    update_data = updated_fields.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    needs_save = False
    for field, value in update_data.items():
        if hasattr(substrate, field) and getattr(substrate, field) != value:
            setattr(substrate, field, value)
            needs_save = True

    if needs_save:
        substrate.updated_at = datetime.now(timezone.utc)
        await substrate.save()

    updated_substrate = await Substrate.get(substrate.id)
    if not updated_substrate:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve updated substrate after saving.",
        )
    return updated_substrate


@substrate_api.delete("/substrates/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_substrate(media_id: str):
    """Delete a specific substrate by its media_id."""
    substrate = await Substrate.find_one(Substrate.media_id == media_id)
    if not substrate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )

    section_count = await Section.find(Section.substrate_ref.id == substrate.id).count()
    if section_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete substrate '{media_id}' as it has {section_count} associated sections.",
        )

    await substrate.delete()

    return None


@substrate_api.get("/substrates/{media_id}/sections", response_model=list[Section])
async def get_substrate_sections(
    media_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve sections associated with a specific substrate, identified by media_id."""
    substrate = await Substrate.find_one(Substrate.media_id == media_id)
    if not substrate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )

    sections = (
        await Section.find(Section.substrate_ref.id == substrate.id, fetch_links=True)
        .sort([("section_number", 1)])
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    return sections
