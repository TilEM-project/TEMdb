from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import AnyHttpUrl
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import BlockResponse, SpecimenCreate, SpecimenResponse, SpecimenUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import BlockSQLModel, SpecimenSQLModel

specimen_api = APIRouter(
    tags=["Specimens"],
)


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
    return (await session.exec(statement.offset(skip).limit(limit))).all()


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
    return (await session.exec(statement)).one()


@specimen_api.get("/specimens/{specimen_id}/blocks", response_model=list[BlockResponse])
async def get_specimen_blocks(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )
    return [block for _, block in rows if block is not None]


@specimen_api.post("/specimens", status_code=status.HTTP_201_CREATED, response_model=SpecimenResponse)
async def create_specimen(
    specimen_data: SpecimenCreate,
    session: AsyncSession = Depends(get_async_session),
):
    existing_specimen = await session.exec(
        select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == specimen_data.specimen_id)
    )
    if existing_specimen.one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Specimen with ID '{specimen_data.specimen_id}' already exists",
        )

    specimen = SpecimenSQLModel(
        specimen_id=specimen_data.specimen_id,
        description=specimen_data.description,
        specimen_images=sorted(specimen_data.specimen_images or []),
        functional_imaging_metadata=specimen_data.functional_imaging_metadata,
        created_at=specimen_data.created_at or datetime.now(timezone.utc),
    )
    session.add(specimen)
    await session.commit()
    await session.refresh(specimen)
    return specimen


@specimen_api.get("/specimens/{specimen_id}", response_model=SpecimenResponse)
async def get_specimen(specimen_id: str, session: AsyncSession = Depends(get_async_session)):
    """Retrieve a specific specimen by its human-readable ID."""
    specimen_result = await session.exec(select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == specimen_id))
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
    specimen_result = await session.exec(select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == specimen_id))
    specimen = specimen_result.one_or_none()
    if specimen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )

    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    needs_save = False
    if "description" in update_data and specimen.description != update_data["description"]:
        specimen.description = update_data["description"]
        needs_save = True
    if "specimen_images" in update_data:
        updated_images = sorted(update_data["specimen_images"] or [])
        if (specimen.specimen_images or []) != updated_images:
            specimen.specimen_images = updated_images
            needs_save = True
    if (
        "functional_imaging_metadata" in update_data
        and specimen.functional_imaging_metadata != update_data["functional_imaging_metadata"]
    ):
        specimen.functional_imaging_metadata = update_data["functional_imaging_metadata"]
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
    specimen_result = await session.exec(select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == specimen_id))
    specimen = specimen_result.one_or_none()
    if specimen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )
    block_count_query = await session.exec(
        select(func.count()).select_from(BlockSQLModel).where(BlockSQLModel.specimen_id == specimen_id)
    )
    block_count = block_count_query.one()
    if block_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete specimen '{specimen_id}' as it has {block_count} associated blocks.",
        )
    await session.delete(specimen)
    await session.commit()
    return None


@specimen_api.post(
    "/specimens/{specimen_id}/images",
    status_code=status.HTTP_200_OK,
    response_model=SpecimenResponse,
)
async def add_specimen_image(
    specimen_id: str,
    image_url: AnyHttpUrl = Body(..., embed=True),
    session: AsyncSession = Depends(get_async_session),
):
    """Add an image URL to a specimen."""
    specimen_result = await session.exec(select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == specimen_id))
    specimen = specimen_result.one_or_none()
    if specimen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )
    images = set(specimen.specimen_images or [])
    image_url_str = str(image_url)
    if image_url_str not in images:
        images.add(image_url_str)
        specimen.specimen_images = sorted(images)
        specimen.updated_at = datetime.now(timezone.utc)
        session.add(specimen)
        await session.commit()
        await session.refresh(specimen)
    return specimen


@specimen_api.delete(
    "/specimens/{specimen_id}/images",
    status_code=status.HTTP_200_OK,
    response_model=SpecimenResponse,
)
async def remove_specimen_image(
    specimen_id: str,
    image_url: AnyHttpUrl = Query(..., description="The URL of the image to remove"),
    session: AsyncSession = Depends(get_async_session),
):
    """Remove an image URL from a specimen using a query parameter."""
    specimen_result = await session.exec(select(SpecimenSQLModel).where(SpecimenSQLModel.specimen_id == specimen_id))
    specimen = specimen_result.one_or_none()
    if specimen is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Specimen with ID '{specimen_id}' not found",
        )
    image_url_str = str(image_url)
    images = set(specimen.specimen_images or [])
    if image_url_str not in images:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image URL '{image_url_str}' not found in specimen '{specimen_id}'",
        )
    images.remove(image_url_str)
    specimen.specimen_images = sorted(images)
    specimen.updated_at = datetime.now(timezone.utc)
    session.add(specimen)
    await session.commit()
    await session.refresh(specimen)
    return specimen
