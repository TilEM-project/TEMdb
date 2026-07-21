from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import BlockCreate, BlockResponse, BlockUpdate, CuttingSessionResponse
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import BlockSQLModel, CuttingSessionSQLModel, SpecimenSQLModel

block_api = APIRouter(
    tags=["Blocks"],
)


@block_api.get("/blocks", response_model=list[BlockResponse])
async def list_blocks(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of blocks, optionally filtered by specimen ID."""
    statement = select(BlockSQLModel)
    if specimen_id:
        statement = statement.where(BlockSQLModel.specimen_id == specimen_id)
    return (await session.execute(statement.offset(skip).limit(limit))).scalars().all()


@block_api.get(
    "/blocks/specimens/{specimen_id}/blocks/{block_id}/cut-sessions",
    response_model=list[CuttingSessionResponse],
)
async def get_block_cut_sessions(
    specimen_id: str,
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve cutting sessions associated with a specific block."""
    rows = (
        (
            await session.execute(
                select(CuttingSessionSQLModel)
                .select_from(BlockSQLModel)
                .outerjoin(
                    CuttingSessionSQLModel,
                    and_(
                        CuttingSessionSQLModel.block_id == BlockSQLModel.block_id,
                        CuttingSessionSQLModel.specimen_id == BlockSQLModel.specimen_id,
                    ),
                )
                .where(
                    BlockSQLModel.block_id == block_id,
                    BlockSQLModel.specimen_id == specimen_id,
                )
                .offset(skip)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )
    cutting_sessions = [c for c in rows if c is not None]
    if not cutting_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cutting sessions found for block '{block_id}' and specimen '{specimen_id}'",
        )
    return cutting_sessions


@block_api.post("/blocks", status_code=status.HTTP_201_CREATED, response_model=BlockResponse)
async def create_block(
    block_data: BlockCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new block associated with a specimen."""
    specimen = await session.scalars(
        select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == block_data.specimen_id)
    )
    specimen_obj = specimen.one_or_none()
    if specimen_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{block_data.specimen_id}' not found",
        )
    existing_block = await session.scalars(
        select(BlockSQLModel).where(
            BlockSQLModel.block_id == block_data.block_id,
            BlockSQLModel.specimen_id == block_data.specimen_id,
        )
    )
    if existing_block.one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Block with ID '{block_data.block_id}' already exists for specimen '{block_data.specimen_id}'"),
        )
    new_block = BlockSQLModel(
        block_id=block_data.block_id,
        specimen_id=block_data.specimen_id,
        microCT_info=block_data.microCT_info,
        created_at=block_data.created_at or datetime.now(timezone.utc),
        description=block_data.description,
    )
    session.add(new_block)
    await session.commit()
    await session.refresh(new_block)
    return new_block


@block_api.get("/blocks/specimens/{specimen_id}/blocks/{block_id}", response_model=BlockResponse)
async def get_block(
    specimen_id: str,
    block_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a specific block by its human-readable ID and specimen ID."""
    block = (
        await session.execute(
            select(BlockSQLModel).where(
                BlockSQLModel.block_id == block_id, BlockSQLModel.specimen_id == specimen_id
            )
        )
    ).scalar_one_or_none()
    if block is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )
    return block


@block_api.patch("/blocks/specimens/{specimen_id}/blocks/{block_id}", response_model=BlockResponse)
async def update_block(
    specimen_id: str,
    block_id: str,
    updated_fields: BlockUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific block."""
    block_obj = (
        await session.execute(
            select(BlockSQLModel).where(
                BlockSQLModel.block_id == block_id, BlockSQLModel.specimen_id == specimen_id
            )
        )
    ).scalar_one_or_none()
    if block_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )
    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    for field, value in update_data.items():
        setattr(block_obj, field, value)
    block_obj.updated_at = datetime.now(timezone.utc)
    session.add(block_obj)
    await session.commit()
    await session.refresh(block_obj)
    return block_obj


@block_api.delete(
    "/blocks/specimens/{specimen_id}/blocks/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_block(
    specimen_id: str,
    block_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a specific block."""
    block = await session.scalars(
        select(BlockSQLModel).where(BlockSQLModel.block_id == block_id, BlockSQLModel.specimen_id == specimen_id)
    )
    block_obj = block.one_or_none()
    if block_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )
    session_count = (
        await session.scalars(
            select(func.count())
            .select_from(CuttingSessionSQLModel)
            .where(
                CuttingSessionSQLModel.block_id == block_id,
                CuttingSessionSQLModel.specimen_id == specimen_id,
            )
        )
    ).one()
    if session_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(f"Cannot delete block '{block_id}' as it has {session_count} associated cutting sessions."),
        )
    await session.delete(block_obj)
    await session.commit()
    return None


@block_api.get("/blocks/specimens/{specimen_id}/blocks", response_model=list[BlockResponse])
async def list_specimen_blocks(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve blocks associated with a specific specimen using specimen's human-readable ID."""
    specimen_exists = (
        await session.execute(select(SpecimenSQLModel.id).where(SpecimenSQLModel.specimen_id == specimen_id))
    ).scalar_one_or_none()
    if specimen_exists is None:
        raise HTTPException(status_code=404, detail=f"Specimen with ID '{specimen_id}' not found")
    return (
        (
            await session.execute(
                select(BlockSQLModel)
                .where(BlockSQLModel.specimen_id == specimen_id)
                .offset(skip)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
