from fastapi import HTTPException, Query, APIRouter, Body
from typing import List
from datetime import datetime

from temdb.models.v2.specimen import Specimen, SpecimenUpdate
from temdb.models.v2.block import Block
from temdb.models.v2.imaging_session import ImagingSession

specimen_api = APIRouter(
    tags=["Specimens"],
)


@specimen_api.get("/specimens", response_model=List[Specimen])
async def list_specimens(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    return await Specimen.find_all().skip(skip).limit(limit).to_list()


@specimen_api.get("/specimens/{specimen_name}/blocks", response_model=List[Block])
async def get_specimen_blocks(
    specimen_name: str, skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    return (
        await Block.find(Block.specimen.id == specimen.id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@specimen_api.get(
    "/specimens/{specimen_name}/imaging-sessions", response_model=List[ImagingSession]
)
async def get_specimen_imaging_sessions(
    specimen_name: str, skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    return (
        await ImagingSession.find(ImagingSession.specimen.id == specimen.id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@specimen_api.post("/specimens", response_model=Specimen)
async def create_specimen(specimen: Specimen):
    existing_specimen = await Specimen.find_one({"name": specimen.name})
    if existing_specimen:
        raise HTTPException(
            status_code=400, detail="Specimen with this name already exists"
        )

    await specimen.insert()
    return specimen


@specimen_api.get("/specimens/{specimen_name}", response_model=Specimen)
async def get_specimen(specimen_name: str):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")
    return specimen


@specimen_api.patch("/specimens/{specimen_name}", response_model=Specimen)
async def update_specimen(
    specimen_name: str, updated_fields: SpecimenUpdate = Body(...)
):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    update_data = updated_fields.model_dump(exclude_unset=True)

    if update_data:
        for field, value in update_data.items():
            setattr(specimen, field, value)

        specimen.updated_at = datetime.now(datetime.timezone.utc)

        await specimen.save()

    return specimen


@specimen_api.delete("/specimens/{specimen_name}", response_model=dict)
async def delete_specimen(specimen_name: str):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    await specimen.delete()
    return {"message": "Specimen deleted successfully"}


@specimen_api.post("/specimens/{specimen_name}/images", response_model=Specimen)
async def add_specimen_image(specimen_name: str, image_url: str):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    specimen.specimen_images.append(image_url)
    specimen.updated_at = datetime.now(datetime.timezone.utc)
    await specimen.save()
    return specimen


@specimen_api.delete("/specimens/{specimen_name}/images", response_model=Specimen)
async def remove_specimen_image(specimen_name: str, image_url: str):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    if image_url not in specimen.specimen_images:
        raise HTTPException(status_code=404, detail="Image not found in specimen")

    specimen.specimen_images.remove(image_url)
    specimen.updated_at = datetime.now(datetime.timezone.utc)
    await specimen.save()
    return specimen
