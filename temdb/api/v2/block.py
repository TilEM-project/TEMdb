from fastapi import HTTPException, Query, Body, APIRouter
from typing import List

from temdb.models.v2.block import Block, BlockCreate, BlockUpdate
from temdb.models.v2.specimen import Specimen
from temdb.models.v2.cutting_session import CuttingSession

block_api = APIRouter(
    tags=["Blocks"],
)


@block_api.get("/blocks", response_model=List[Block])
async def list_blocks(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    return await Block.find_all().skip(skip).limit(limit).to_list()


@block_api.get(
    "/blocks/{specimen_name}/{block_id}/cut-sessions",
    response_model=List[CuttingSession],
)
async def get_block_cut_sessions(
    specimen_name: str,
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find_one({"specimen.id": specimen.id, "block_id": block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    return (
        await CuttingSession.find(CuttingSession.block.id == block.id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@block_api.post("/blocks", response_model=Block)
async def create_block(block: BlockCreate):
    specimen = await Specimen.get(block.specimen_id)
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    new_block = Block(
        block_id=block.block_id,
        name=block.name,
        microCT_Info=block.microCT_Info,
        specimen=specimen,
    )
    await new_block.insert()
    return new_block


@block_api.get("/blocks/{specimen_name}/{block_id}", response_model=Block)
async def get_block(specimen_name: str, block_id: str):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find_one({"specimen.id": specimen.id, "block_id": block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return block


@block_api.patch("/blocks/{specimen_name}/{block_id}", response_model=Block)
async def update_block(
    specimen_name: str, block_id: str, updated_fields: BlockUpdate = Body(...)
):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find_one({"specimen.id": specimen.id, "block_id": block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    update_data = updated_fields.model_dump(exclude_unset=True)

    if update_data:
        for field, value in update_data.items():
            setattr(block, field, value)

        await block.save()

    return block


@block_api.delete("/blocks/{specimen_name}/{block_id}", response_model=dict)
async def delete_block(specimen_name: str, block_id: str):
    specimen = await Specimen.find_one({"name": specimen_name})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find_one({"specimen.id": specimen.id, "block_id": block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    await block.delete()
    return {"message": "Block deleted successfully"}


@block_api.get("/specimens/{specimen_name}/blocks", response_model=List[Block])
async def list_specimen_blocks(
    specimen_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
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
