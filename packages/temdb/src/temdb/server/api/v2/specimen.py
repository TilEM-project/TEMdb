from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import BlockResponse, SpecimenCreate, SpecimenResponse, SpecimenUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import BlockSQLModel, SpecimenSQLModel

from ..utils import drop_null_keys, merge_extra

specimen_api = APIRouter(
    tags=["Specimens"],
)


def _to_json_compatible(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return jsonable_encoder(value)


@specimen_api.get("/specimens", response_model=list[SpecimenResponse])
async def list_specimens(
    search: str | None = Query(None, description="Search term for specimen ID or description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    statement = select(SpecimenSQLModel)
    if search:
        like_pattern = f"%{search}%"
        statement = statement.where(
            or_(
                SpecimenSQLModel.specimen_id.ilike(like_pattern),
                SpecimenSQLModel.description.ilike(like_pattern),
            )
        )
    return (await session.scalars(statement.order_by(SpecimenSQLModel.specimen_id).offset(skip).limit(limit))).all()


@specimen_api.get("/specimens/count", response_model=int)
async def count_specimens(
    search: str | None = Query(None, description="Search term for specimen ID or description"),
    session: AsyncSession = Depends(get_async_session),
):
    statement = select(func.count()).select_from(SpecimenSQLModel)
    if search:
        like_pattern = f"%{search}%"
        statement = statement.where(
            or_(
                SpecimenSQLModel.specimen_id.ilike(like_pattern),
                SpecimenSQLModel.description.ilike(like_pattern),
            )
        )
    return (await session.scalars(statement)).one()


@specimen_api.get("/specimens/{specimen_id}/blocks", response_model=list[BlockResponse])
async def get_specimen_blocks(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    if await session.scalar(select(SpecimenSQLModel.id).where(SpecimenSQLModel.specimen_id == specimen_id)) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )
    blocks = await session.scalars(
        select(BlockSQLModel)
        .where(BlockSQLModel.specimen_id == specimen_id)
        .order_by(BlockSQLModel.block_id)
        .offset(skip)
        .limit(limit)
    )
    return blocks.all()


@specimen_api.post("/specimens", status_code=status.HTTP_201_CREATED, response_model=SpecimenResponse)
async def create_specimen(
    specimen_data: SpecimenCreate,
    session: AsyncSession = Depends(get_async_session),
):
    existing_specimen = await session.scalars(
        select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == specimen_data.specimen_id)
    )
    if existing_specimen.one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Specimen with ID '{specimen_data.specimen_id}' already exists",
        )

    specimen = SpecimenSQLModel(
        specimen_id=specimen_data.specimen_id,
        description=specimen_data.description,
        functional_imaging_metadata=specimen_data.functional_imaging_metadata,
        created_at=specimen_data.created_at or datetime.now(timezone.utc),
        extra=drop_null_keys(specimen_data.extra),
    )
    session.add(specimen)
    await session.commit()
    await session.refresh(specimen)
    return specimen


@specimen_api.get("/specimens/{specimen_id}", response_model=SpecimenResponse)
async def get_specimen(specimen_id: str, session: AsyncSession = Depends(get_async_session)):
    """Retrieve a specific specimen by its human-readable ID."""
    specimen_result = await session.scalars(select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == specimen_id))
    specimen = specimen_result.one_or_none()
    if specimen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )
    return specimen


@specimen_api.patch("/specimens/{specimen_id}", response_model=SpecimenResponse)
async def update_specimen(
    specimen_id: str,
    updated_fields: SpecimenUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific specimen."""
    specimen_result = await session.scalars(select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == specimen_id))
    specimen = specimen_result.one_or_none()
    if specimen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )

    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    extra_changes = update_data.pop("extra", None)

    needs_save = False
    if "description" in update_data and specimen.description != update_data["description"]:
        specimen.description = update_data["description"]
        needs_save = True
    if (
        "functional_imaging_metadata" in update_data
        and specimen.functional_imaging_metadata != update_data["functional_imaging_metadata"]
    ):
        specimen.functional_imaging_metadata = update_data["functional_imaging_metadata"]
        needs_save = True

    if extra_changes is not None:
        specimen.extra = merge_extra(SpecimenSQLModel.extra, extra_changes)
        needs_save = True

    if needs_save:
        specimen.updated_at = datetime.now(timezone.utc)
        session.add(specimen)
        await session.commit()
        await session.refresh(specimen)
    return specimen


@specimen_api.delete("/specimens/{specimen_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_specimen(specimen_id: str, session: AsyncSession = Depends(get_async_session)):
    """Delete a specific specimen."""
    specimen_result = await session.scalars(select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == specimen_id))
    specimen = specimen_result.one_or_none()
    if specimen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )
    await session.delete(specimen)
    await session.commit()
    return None
