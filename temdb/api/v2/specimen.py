from datetime import timezone
from fastapi import HTTPException, Query, APIRouter, Body, status
from typing import List
from datetime import datetime
from pydantic import AnyHttpUrl

from temdb.models.v2.specimen import Specimen, SpecimenCreate, SpecimenUpdate
from temdb.models.v2.block import Block

specimen_api = APIRouter(
    tags=["Specimens"],
)


@specimen_api.get("/specimens", response_model=List[Specimen])
async def list_specimens(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    return await Specimen.find_all(fetch_links=True).skip(skip).limit(limit).to_list()


@specimen_api.get("/specimens/{specimen_id}/blocks", response_model=List[Block])
async def get_specimen_blocks(
    specimen_id: str, skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    specimen = await Specimen.find_one(Specimen.specimen_id == specimen_id)
    if not specimen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )
    return (
        await Block.find(Block.specimen_id == specimen.specimen_id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@specimen_api.post(
    "/specimens", response_model=Specimen, status_code=status.HTTP_201_CREATED
)
async def create_specimen(specimen_data: SpecimenCreate):
    existing_specimen = await Specimen.find_one(
        {"specimen_id": specimen_data.specimen_id}
    )
    if existing_specimen:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Specimen with ID '{specimen_data.specimen_id}' already exists",
        )

    specimen = Specimen(
        specimen_id=specimen_data.specimen_id,
        description=specimen_data.description,
        specimen_images=specimen_data.specimen_images or set(),
        created_at=datetime.now(timezone.utc),
        updated_at=None,
        functional_imaging_metadata=specimen_data.functional_imaging_metadata,
    )

    await specimen.insert()
    return specimen


@specimen_api.get("/specimens/{specimen_id}", response_model=Specimen)
async def get_specimen(specimen_id: str):
    """Retrieve a specific specimen by its human-readable ID."""
    specimen = await Specimen.find_one(
        Specimen.specimen_id == specimen_id, fetch_links=True
    )
    if not specimen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )
    return specimen


@specimen_api.patch("/specimens/{specimen_id}", response_model=Specimen)
async def update_specimen(specimen_id: str, updated_fields: SpecimenUpdate = Body(...)):
    """Update details of a specific specimen."""
    specimen = await Specimen.find_one(Specimen.specimen_id == specimen_id)
    if not specimen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )

    update_data = updated_fields.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided"
        )

    needs_save = False
    if (
        "description" in update_data
        and specimen.description != update_data["description"]
    ):
        specimen.description = update_data["description"]
        needs_save = True
    if (
        "specimen_images" in update_data
        and specimen.specimen_images != update_data["specimen_images"]
    ):
        specimen.specimen_images = (
            set(update_data["specimen_images"])
            if update_data["specimen_images"] is not None
            else set()
        )
        needs_save = True
    if (
        "functional_imaging_metadata" in update_data
        and specimen.functional_imaging_metadata
        != update_data["functional_imaging_metadata"]
    ):
        specimen.functional_imaging_metadata = update_data[
            "functional_imaging_metadata"
        ]
        needs_save = True

    if needs_save:
        specimen.updated_at = datetime.now(timezone.utc)
        await specimen.save()

    updated_specimen = await Specimen.get(specimen.id, fetch_links=True)
    return updated_specimen


@specimen_api.delete("/specimens/{specimen_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_specimen(specimen_id: str):
    """Delete a specific specimen."""
    specimen = await Specimen.find_one(Specimen.specimen_id == specimen_id)
    if not specimen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )

    block_count = await Block.find(
        Block.specimen_ref.id == specimen.id
    ).count()

    if block_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete specimen '{specimen_id}' as it has {block_count} associated blocks.",
        )

    await specimen.delete()
    return None


@specimen_api.post(
    "/specimens/{specimen_id}/images",
    response_model=Specimen,
    status_code=status.HTTP_200_OK,
)
async def add_specimen_image(
    specimen_id: str, image_url: AnyHttpUrl = Body(..., embed=True)
):
    """Add an image URL to a specimen."""
    specimen = await Specimen.find_one(Specimen.specimen_id == specimen_id)
    if not specimen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )

    if specimen.specimen_images is None:
        specimen.specimen_images = set()

    if str(image_url) in specimen.specimen_images:
        fetched_specimen = await Specimen.get(
            specimen.id, fetch_links=True
        )  # Return current state
        return fetched_specimen

    specimen.specimen_images.add(str(image_url))
    specimen.updated_at = datetime.now(timezone.utc)
    await specimen.save()

    updated_specimen = await Specimen.get(specimen.id, fetch_links=True)
    return updated_specimen



@specimen_api.delete(
    "/specimens/{specimen_id}/images",
    response_model=Specimen,
    status_code=status.HTTP_200_OK,
)
async def remove_specimen_image(
    specimen_id: str,
    image_url: AnyHttpUrl = Query(..., description="The URL of the image to remove") 
):
    """Remove an image URL from a specimen using a query parameter.""" 
    specimen = await Specimen.find_one(Specimen.specimen_id == specimen_id)
    if not specimen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )

    image_url_str = str(image_url)

    if (
        specimen.specimen_images is None
        or image_url_str not in specimen.specimen_images
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image URL '{image_url_str}' not found in specimen '{specimen_id}'",
        )

    specimen.specimen_images.remove(image_url_str)
    specimen.updated_at = datetime.now(timezone.utc) 
    await specimen.save()

    updated_specimen = await Specimen.get(specimen.id, fetch_links=True)
    return updated_specimen