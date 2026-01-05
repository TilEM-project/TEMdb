from fastapi import APIRouter, Body, HTTPException, Query, status
from temdb.models import BlockCreate, BlockUpdate
from temdb.server.documents import (
    BlockDocument as Block,
)
from temdb.server.documents import (
    CuttingSessionDocument as CuttingSession,
)
from temdb.server.documents import (
    SpecimenDocument as Specimen,
)

block_api = APIRouter(
    tags=["Blocks"],
)


@block_api.get("/blocks", response_model=list[Block])
async def list_blocks(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve a list of blocks, optionally filtered by specimen ID."""
    query_filter = {}
    if specimen_id:
        query_filter["specimen_id"] = specimen_id

    return await Block.find(query_filter, fetch_links=True).skip(skip).limit(limit).to_list()


@block_api.get(
    "/blocks/specimens/{specimen_id}/blocks/{block_id}/cut-sessions",
    response_model=list[CuttingSession],
)
async def get_block_cut_sessions(
    specimen_id: str,
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve cutting sessions associated with a specific block."""
    block = await Block.find_one({"block_id": block_id, "specimen_id": specimen_id})
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )

    cutting_sessions = (
        await CuttingSession.find(
            CuttingSession.block_ref.id == block.id,
            fetch_links=True,
        )
        .skip(skip)
        .limit(limit)
        .to_list()
    )
    if not cutting_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cutting sessions found for block '{block_id}' and specimen '{specimen_id}'",
        )

    return cutting_sessions


@block_api.post("/blocks", response_model=Block, status_code=status.HTTP_201_CREATED)
async def create_block(block_data: BlockCreate):
    """Create a new block associated with a specimen."""
    specimen = await Specimen.find_one(Specimen.specimen_id == block_data.specimen_id)
    if not specimen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{block_data.specimen_id}' not found",
        )

    existing_block = await Block.find_one({"block_id": block_data.block_id, "specimen_ref.id": specimen.id})
    if existing_block:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Block with ID '{block_data.block_id}' already exists for specimen '{block_data.specimen_id}'"),
        )

    new_block = Block(
        block_id=block_data.block_id,
        specimen_id=specimen.specimen_id,
        specimen_ref=specimen.id,
        microCT_info=block_data.microCT_info,
    )
    await new_block.insert()
    created_block = await Block.get(new_block.id, fetch_links=True)
    return created_block


@block_api.get("/blocks/specimens/{specimen_id}/blocks/{block_id}", response_model=Block)
async def get_block(specimen_id: str, block_id: str):
    """Retrieve a specific block by its human-readable ID and specimen ID."""
    block = await Block.find_one({"block_id": block_id, "specimen_id": specimen_id}, fetch_links=True)
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )
    return block


@block_api.patch("/blocks/specimens/{specimen_id}/blocks/{block_id}", response_model=Block)
async def update_block(specimen_id: str, block_id: str, updated_fields: BlockUpdate = Body(...)):
    """Update details of a specific block."""
    block = await Block.find_one({"block_id": block_id, "specimen_id": specimen_id})
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )

    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    needs_save = False
    if "microCT_info" in update_data and block.microCT_info != update_data["microCT_info"]:
        block.microCT_info = update_data["microCT_info"]
        needs_save = True

    if needs_save:
        await block.save()

    updated_block = await Block.get(block.id, fetch_links=True)
    return updated_block


@block_api.delete(
    "/blocks/specimens/{specimen_id}/blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_block(specimen_id: str, block_id: str):
    """Delete a specific block."""
    block = await Block.find_one({"block_id": block_id, "specimen_id": specimen_id})
    if not block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )

    session_count = await CuttingSession.find(CuttingSession.block_ref.id == block.id).count()
    if session_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Cannot delete block '{block_id}' as it has {session_count} associated cutting sessions."),
        )

    await block.delete()
    return None


@block_api.get("/blocks/specimens/{specimen_id}/blocks", response_model=list[Block])
async def list_specimen_blocks(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve blocks associated with a specific specimen using specimen's human-readable ID."""
    blocks = await Block.find({"specimen_id": specimen_id}, fetch_links=True).skip(skip).limit(limit).to_list()
    if not blocks and not await Specimen.find_one(Specimen.specimen_id == specimen_id):
        raise HTTPException(status_code=404, detail=f"Specimen with ID '{specimen_id}' not found")

    return blocks
