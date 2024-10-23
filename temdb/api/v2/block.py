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
    "/blocks/{specimen_id}/{block_id}/cut-sessions",
    response_model=List[CuttingSession],
)
async def get_block_cut_sessions(
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


@block_api.post("/blocks", response_model=Block)
async def create_block(block: BlockCreate):
    specimen = await Specimen.find_one({"specimen_id": block.specimen_id})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")
    try:
        new_block = Block(
            block_id=block.block_id,
            microCT_info=block.microCT_info,
            specimen_id=specimen.id,
        )
        await new_block.insert()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return new_block


@block_api.get("/blocks/{specimen_id}/{block_id}", response_model=Block)
async def get_block(specimen_id: str, block_id: str):
    specimen = await Specimen.find_one({"specimen_id": specimen_id})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find(Block.block_id == block_id, Block.specimen_id.id == specimen.id).first_or_none()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return block


@block_api.patch("/blocks/{specimen_id}/{block_id}", response_model=Block)
async def update_block(
    specimen_id: str, block_id: str, updated_fields: BlockUpdate = Body(...)
):
    specimen = await Specimen.find_one({"specimen_id": specimen_id})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find_one({"specimen_id": specimen.id, "block_id": block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    update_data = updated_fields.model_dump(exclude_unset=True)

    if update_data:
        for field, value in update_data.items():
            setattr(block, field, value)

        await block.save()

    return block


@block_api.delete("/blocks/{specimen_id}/{block_id}", response_model=dict)
async def delete_block(specimen_id: str, block_id: str):
    specimen = await Specimen.find_one({"specimen_id": specimen_id})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    block = await Block.find_one({"specimen_id": specimen.id, "block_id": block_id})
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")

    await block.delete()
    return {"message": "Block deleted successfully"}


@block_api.get("/blocks/specimens/{specimen_id}/blocks", response_model=List[Block])
async def list_specimen_blocks(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    specimen = await Specimen.find_one({"specimen_id": specimen_id})
    if not specimen:
        raise HTTPException(status_code=404, detail="Specimen not found")

    return (
        await Block.find(Block.specimen_id.id == specimen.id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )
