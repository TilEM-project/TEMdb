from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import BlockCreate, BlockUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import BlockSQLModel, CuttingSessionSQLModel, SpecimenSQLModel

block_api = APIRouter(
    tags=["Blocks"],
)


def _sql_block_payload(block: BlockSQLModel, specimen_internal_id: int | None = None) -> dict:
    return {
        "_id": str(block.id),
        "block_id": block.block_id,
        "specimen_id": block.specimen_id,
        "specimen_ref": {"id": str(specimen_internal_id)} if specimen_internal_id is not None else None,
        "microCT_info": block.microCT_info,
        "created_at": block.created_at,
        "updated_at": block.updated_at,
    }


@block_api.get("/blocks")
async def list_blocks(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of blocks, optionally filtered by specimen ID."""
    statement = (
        select(BlockSQLModel, SpecimenSQLModel.id)
        .select_from(BlockSQLModel)
        .outerjoin(SpecimenSQLModel, SpecimenSQLModel.specimen_id == BlockSQLModel.specimen_id)
    )
    if specimen_id:
        statement = statement.where(BlockSQLModel.specimen_id == specimen_id)
    rows = (await session.execute(statement.offset(skip).limit(limit))).all()
    return [_sql_block_payload(block, specimen_ref) for block, specimen_ref in rows]


@block_api.get(
    "/blocks/specimens/{specimen_id}/blocks/{block_id}/cut-sessions",
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
        await session.execute(
            select(
                BlockSQLModel.id,
                SpecimenSQLModel.id,
                CuttingSessionSQLModel,
            )
            .select_from(BlockSQLModel)
            .outerjoin(SpecimenSQLModel, SpecimenSQLModel.specimen_id == BlockSQLModel.specimen_id)
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
    ).all()
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )
    block_internal_id, specimen_internal_id, _ = rows[0]
    cutting_sessions = [row[2] for row in rows if row[2] is not None]
    if not cutting_sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cutting sessions found for block '{block_id}' and specimen '{specimen_id}'",
        )
    return [
        {
            "_id": str(c.id),
            "cutting_session_id": c.cutting_session_id,
            "specimen_id": c.specimen_id,
            "block_id": c.block_id,
            "block_ref": {"id": str(block_internal_id)} if block_internal_id is not None else None,
            "specimen_ref": {"id": str(specimen_internal_id)} if specimen_internal_id is not None else None,
            "start_time": c.start_time,
            "end_time": c.end_time,
            "operator": c.operator,
            "sectioning_device": c.sectioning_device,
            "media_type": c.media_type,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }
        for c in cutting_sessions
    ]


@block_api.post("/blocks", status_code=status.HTTP_201_CREATED)
async def create_block(
    block_data: BlockCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new block associated with a specimen."""
    specimen = await session.exec(
        select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == block_data.specimen_id)
    )
    specimen_obj = specimen.one_or_none()
    if specimen_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{block_data.specimen_id}' not found",
        )
    existing_block = await session.exec(
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
    )
    session.add(new_block)
    await session.commit()
    await session.refresh(new_block)
    return _sql_block_payload(new_block, specimen_obj.id)


@block_api.get("/blocks/specimens/{specimen_id}/blocks/{block_id}")
async def get_block(
    specimen_id: str,
    block_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a specific block by its human-readable ID and specimen ID."""
    row = (
        await session.execute(
            select(BlockSQLModel, SpecimenSQLModel.id)
            .select_from(BlockSQLModel)
            .outerjoin(SpecimenSQLModel, SpecimenSQLModel.specimen_id == BlockSQLModel.specimen_id)
            .where(BlockSQLModel.block_id == block_id, BlockSQLModel.specimen_id == specimen_id)
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )
    block_obj, specimen_ref = row
    return _sql_block_payload(block_obj, specimen_ref)


@block_api.patch("/blocks/specimens/{specimen_id}/blocks/{block_id}")
async def update_block(
    specimen_id: str,
    block_id: str,
    updated_fields: BlockUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific block."""
    row = (
        await session.execute(
            select(BlockSQLModel, SpecimenSQLModel.id)
            .select_from(BlockSQLModel)
            .outerjoin(SpecimenSQLModel, SpecimenSQLModel.specimen_id == BlockSQLModel.specimen_id)
            .where(BlockSQLModel.block_id == block_id, BlockSQLModel.specimen_id == specimen_id)
        )
    ).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )
    block_obj, specimen_ref = row
    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    if "microCT_info" in update_data and block_obj.microCT_info != update_data["microCT_info"]:
        block_obj.microCT_info = update_data["microCT_info"]
        block_obj.updated_at = datetime.now(timezone.utc)
        session.add(block_obj)
        await session.commit()
        await session.refresh(block_obj)
    return _sql_block_payload(block_obj, specimen_ref)


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
    block = await session.exec(
        select(BlockSQLModel).where(BlockSQLModel.block_id == block_id, BlockSQLModel.specimen_id == specimen_id)
    )
    block_obj = block.one_or_none()
    if block_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block with ID '{block_id}' for specimen '{specimen_id}' not found",
        )
    session_count = (
        await session.exec(
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


@block_api.get("/blocks/specimens/{specimen_id}/blocks")
async def list_specimen_blocks(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve blocks associated with a specific specimen using specimen's human-readable ID."""
    rows = (
        await session.execute(
            select(SpecimenSQLModel.id, BlockSQLModel)
            .select_from(SpecimenSQLModel)
            .outerjoin(BlockSQLModel, BlockSQLModel.specimen_id == SpecimenSQLModel.specimen_id)
            .where(SpecimenSQLModel.specimen_id == specimen_id)
            .offset(skip)
            .limit(limit)
        )
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Specimen with ID '{specimen_id}' not found")
    specimen_ref = rows[0][0]
    return [_sql_block_payload(block, specimen_ref) for _, block in rows if block is not None]
