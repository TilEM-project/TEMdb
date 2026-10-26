import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import (
    ApertureStatus,
    APIErrorResponse,
    FileObject,
    FileObjectRequest,
    FileObjectResponse,
    SectionCreate,
    SectionQuality,
    SectionResponse,
    SectionUpdate,
    StorageProtocol,
)
from temdb.server.config import config
from temdb.server.dependencies import get_async_session
from temdb.server.exception_handlers import BaseError
from temdb.server.sqlmodels import (
    BlockSQLModel,
    CuttingSessionSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SubstrateSQLModel,
)

from ..utils import drop_null_keys, merge_extra

section_api = APIRouter(
    tags=["Sections"],
)

logger = logging.getLogger(__name__)


def _to_json_compatible(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return jsonable_encoder(value)


def check_aperture_index(aperture_index: int | None, aperture_count: int, media_id: str) -> None:
    """Refuse an aperture index the substrate's layout does not have."""
    if aperture_index is not None and aperture_index >= aperture_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Substrate '{media_id}' has no aperture {aperture_index}; its layout has {aperture_count}",
        )


async def mark_apertures_used(session: AsyncSession, media_id: str, aperture_indexes: list[int | None]) -> None:
    """Mark the apertures sections were placed on as used; damaged or already used apertures are left as they are."""
    indexes = {index for index in aperture_indexes if index is not None}
    if not indexes:
        return
    substrate = await session.scalar(
        select(SubstrateSQLModel)
        .where(SubstrateSQLModel.media_id == media_id)
        .with_for_update(key_share=True)
        .execution_options(populate_existing=True)
    )
    statuses = list(substrate.aperture_status)
    for index in indexes:
        if statuses[index] == ApertureStatus.AVAILABLE.value:
            statuses[index] = ApertureStatus.USED.value
    if statuses != substrate.aperture_status:
        substrate.aperture_status = statuses
        substrate.updated_at = datetime.now(timezone.utc)


async def section_or_404(session: AsyncSession, section_id: str) -> SectionSQLModel:
    section_obj = await session.scalar(select(SectionSQLModel).where(SectionSQLModel.section_id == section_id))
    if section_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Section '{section_id}' not found")
    return section_obj


def dump_position(position):
    return position.model_dump(mode="json") if position is not None else None


@section_api.get("/sections", response_model=list[SectionResponse])
async def list_sections(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    cutting_session_id: str | None = Query(None, description="Filter by human-readable Cutting Session ID"),
    media_id: str | None = Query(None, description="Filter by media ID"),
    quality: SectionQuality | None = Query(None, description="Filter by section quality"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of sections with optional filters and pagination."""
    statement = select(SectionSQLModel)
    if specimen_id:
        statement = statement.where(SectionSQLModel.specimen_id == specimen_id)
    if block_id:
        statement = statement.where(SectionSQLModel.block_id == block_id)
    if cutting_session_id:
        statement = statement.where(SectionSQLModel.cutting_session_id == cutting_session_id)
    if media_id:
        statement = statement.where(SectionSQLModel.media_id == media_id)
    if quality:
        statement = statement.where(SectionSQLModel.section_metrics["quality"].as_string() == quality.value)
    statement = statement.order_by(SectionSQLModel.cutting_session_id, SectionSQLModel.section_number)
    return (await session.scalars(statement.offset(skip).limit(limit))).all()


@section_api.get("/sections/count", response_model=int)
async def count_sections(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    cutting_session_id: str | None = Query(None, description="Filter by human-readable Cutting Session ID"),
    media_id: str | None = Query(None, description="Filter by media ID"),
    quality: SectionQuality | None = Query(None, description="Filter by section quality"),
    session: AsyncSession = Depends(get_async_session),
):
    statement = select(func.count()).select_from(SectionSQLModel)
    conditions = []
    if specimen_id:
        conditions.append(SectionSQLModel.specimen_id == specimen_id)
    if block_id:
        conditions.append(SectionSQLModel.block_id == block_id)
    if cutting_session_id:
        conditions.append(SectionSQLModel.cutting_session_id == cutting_session_id)
    if media_id:
        conditions.append(SectionSQLModel.media_id == media_id)
    if quality:
        conditions.append(SectionSQLModel.section_metrics["quality"].as_string() == quality.value)
    if conditions:
        statement = statement.where(and_(*conditions))
    return (await session.scalars(statement)).one()


@section_api.get("/sections/sessions/{cutting_session_id}", response_model=list[SectionResponse])
async def list_cutting_session_sections(
    cutting_session_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections associated with a specific cutting session using its human-readable ID."""
    rows = (
        await session.execute(
            select(CuttingSessionSQLModel.id, SectionSQLModel)
            .select_from(CuttingSessionSQLModel)
            .outerjoin(
                SectionSQLModel,
                SectionSQLModel.cutting_session_id == CuttingSessionSQLModel.cutting_session_id,
            )
            .where(CuttingSessionSQLModel.cutting_session_id == cutting_session_id)
            .order_by(SectionSQLModel.section_number)
        )
    ).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Cutting Session '{cutting_session_id}' not found")
    sections = [row[1] for row in rows if row[1] is not None]
    return sections[skip : skip + limit]


@section_api.get("/sections/blocks/{block_id}", response_model=list[SectionResponse])
async def list_block_sections(
    block_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections associated with a specific block using its human-readable ID."""
    sections = await session.scalars(
        select(SectionSQLModel)
        .where(SectionSQLModel.block_id == block_id)
        .order_by(SectionSQLModel.cutting_session_id, SectionSQLModel.section_number)
        .offset(skip)
        .limit(limit)
    )
    return sections.all()


@section_api.get("/sections/specimens/{specimen_id}", response_model=list[SectionResponse])
async def list_specimen_sections(
    specimen_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections associated with a specific specimen using its human-readable ID."""
    sections = await session.scalars(
        select(SectionSQLModel)
        .where(SectionSQLModel.specimen_id == specimen_id)
        .order_by(SectionSQLModel.block_id, SectionSQLModel.cutting_session_id, SectionSQLModel.section_number)
        .offset(skip)
        .limit(limit)
    )
    return sections.all()


@section_api.get("/sections/{section_id}", response_model=SectionResponse)
async def get_section(
    section_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a section by its section_id."""
    return await section_or_404(session, section_id)


def _section_row(data: SectionCreate, cut_session: CuttingSessionSQLModel) -> SectionSQLModel:
    """The section a create asks for, without its number and section_id, which are assigned when it is new."""
    return SectionSQLModel(
        cut_count=data.cut_count,
        timestamp=data.timestamp,
        cutting_session_id=cut_session.cutting_session_id,
        block_id=cut_session.block_id,
        specimen_id=cut_session.specimen_id,
        media_id=data.media_id,
        optical_image=_to_json_compatible(data.optical_image) if data.optical_image is not None else None,
        aperture_index=data.aperture_index,
        position=dump_position(data.position),
        condition=data.condition,
        condition_reason=data.condition_reason,
        section_metrics=data.section_metrics.model_dump(mode="json") if data.section_metrics is not None else None,
        run_parameters=data.run_parameters.model_dump(mode="json") if data.run_parameters is not None else None,
        created_at=data.created_at or datetime.now(timezone.utc),
        extra=drop_null_keys(data.extra),
    )


async def _stored_at_placement(session: AsyncSession, row: SectionSQLModel) -> SectionSQLModel | None:
    """The stored section with the row's (media_id, aperture_index, timestamp), raising 409 KEY_IN_USE if it differs."""
    stored = await session.scalar(
        select(SectionSQLModel).where(
            SectionSQLModel.media_id == row.media_id,
            SectionSQLModel.aperture_index.is_not_distinct_from(row.aperture_index),
            SectionSQLModel.timestamp == row.timestamp,
        )
    )
    if stored is None:
        return None
    compared = (
        "cutting_session_id",
        "cut_count",
        "optical_image",
        "position",
        "section_metrics",
        "run_parameters",
        "extra",
    )
    differing = [field for field in compared if getattr(stored, field) != getattr(row, field)]
    if differing:
        raise BaseError(
            f"Section '{stored.section_id}' is already at this placement with different {', '.join(differing)}",
            status_code=status.HTTP_409_CONFLICT,
            error_code="KEY_IN_USE",
        )
    return stored


async def lock_substrate(session: AsyncSession, media_id: str) -> SubstrateSQLModel:
    """The substrate, locked so section and ROI numbers are handed out one create at a time; 404 if missing."""
    substrate = await session.scalar(
        select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id).with_for_update(key_share=True)
    )
    if substrate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Substrate '{media_id}' not found")
    return substrate


async def _cutting_session(session: AsyncSession, cutting_session_id: str) -> CuttingSessionSQLModel:
    cut_session = await session.scalar(
        select(CuttingSessionSQLModel).where(CuttingSessionSQLModel.cutting_session_id == cutting_session_id)
    )
    if cut_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Cutting Session with ID '{cutting_session_id}' not found"
        )
    return cut_session


async def _number(session: AsyncSession, row: SectionSQLModel) -> None:
    """Give a new section the next number on its substrate; the caller holds the substrate lock."""
    highest = await session.scalar(
        select(func.max(SectionSQLModel.section_number)).where(SectionSQLModel.media_id == row.media_id)
    )
    row.section_number = (highest or 0) + 1
    row.section_id = f"{row.media_id}_S{row.section_number}"


@section_api.post(
    "/sections",
    status_code=status.HTTP_201_CREATED,
    response_model=SectionResponse,
    responses={
        status.HTTP_200_OK: {"model": SectionResponse, "description": "The section was already stored"},
        status.HTTP_409_CONFLICT: {"model": APIErrorResponse, "description": "Same placement, different values"},
    },
)
async def create_section(
    section_data: SectionCreate,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a section, numbered next on its substrate; a section already at this placement is returned (200)."""
    cut_session = await _cutting_session(session, section_data.cutting_session_id)
    substrate = await lock_substrate(session, section_data.media_id)
    check_aperture_index(section_data.aperture_index, len(substrate.aperture_status), section_data.media_id)
    row = _section_row(section_data, cut_session)
    stored = await _stored_at_placement(session, row)
    if stored is not None:
        response.status_code = status.HTTP_200_OK
        return stored
    await _number(session, row)
    session.add(row)
    await mark_apertures_used(session, row.media_id, [row.aperture_index])
    await session.commit()
    await session.refresh(row)
    return row


@section_api.post(
    "/sections/batch",
    status_code=status.HTTP_201_CREATED,
    summary="Create multiple Sections in bulk",
    response_model=list[SectionResponse],
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": APIErrorResponse, "description": "Invalid input data"},
        status.HTTP_404_NOT_FOUND: {"model": APIErrorResponse, "description": "Parent resource not found"},
        status.HTTP_409_CONFLICT: {"model": APIErrorResponse, "description": "Same placement, different values"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": APIErrorResponse, "description": "Internal server error"},
    },
)
async def create_sections_batch(
    sections_data: list[SectionCreate],
    session: AsyncSession = Depends(get_async_session),
):
    """Create sections in request order, each as POST /sections would; nothing is stored if any item fails."""
    if not sections_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section data list cannot be empty.",
        )
    placements = [(item.media_id, item.aperture_index, item.timestamp) for item in sections_data]
    if len(set(placements)) != len(placements):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="a placement (media_id, aperture_index, timestamp) appears more than once in the batch",
        )
    sessions = {
        sid: await _cutting_session(session, sid) for sid in {item.cutting_session_id for item in sections_data}
    }
    substrates = {media_id: await lock_substrate(session, media_id) for media_id in sorted({p[0] for p in placements})}
    result = []
    for item in sections_data:
        check_aperture_index(item.aperture_index, len(substrates[item.media_id].aperture_status), item.media_id)
        row = _section_row(item, sessions[item.cutting_session_id])
        stored = await _stored_at_placement(session, row)
        if stored is not None:
            result.append(stored)
            continue
        await _number(session, row)
        session.add(row)
        await session.flush()
        result.append(row)
    for media_id in substrates:
        await mark_apertures_used(
            session, media_id, [item.aperture_index for item in sections_data if item.media_id == media_id]
        )
    await session.commit()
    for row in result:
        await session.refresh(row)
    return result


@section_api.patch("/sections/{section_id}", response_model=SectionResponse)
async def update_section(
    section_id: str,
    updated_fields: SectionUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update a section by its section_id."""
    section_obj = await section_or_404(session, section_id)
    update_data = updated_fields.model_dump(
        exclude_unset=True,
    )
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    extra_changes = update_data.pop("extra", None)
    metrics = update_data.pop("section_metrics", None)
    if metrics is not None:
        section_obj.section_metrics = jsonable_encoder(metrics)
    run_parameters = update_data.pop("run_parameters", None)
    if run_parameters is not None:
        section_obj.run_parameters = jsonable_encoder(run_parameters)
    optical_image = update_data.pop("optical_image", None)
    if optical_image is not None:
        section_obj.optical_image = jsonable_encoder(optical_image)
    if "aperture_index" in update_data and update_data["aperture_index"] != section_obj.aperture_index:
        rois = (await session.scalars(select(ROISQLModel.roi_id).where(ROISQLModel.section_id == section_id))).all()
        if rois:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Section '{section_id}' cannot move to another aperture while ROIs {', '.join(rois)} are on it",
            )
    if update_data.get("aperture_index") is not None:
        aperture_count = await session.scalar(
            select(func.cardinality(SubstrateSQLModel.aperture_status)).where(
                SubstrateSQLModel.media_id == section_obj.media_id
            )
        )
        check_aperture_index(update_data["aperture_index"], aperture_count, section_obj.media_id)
    for field, value in update_data.items():
        setattr(section_obj, field, value)
    if extra_changes is not None:
        section_obj.extra = merge_extra(SectionSQLModel.extra, extra_changes)
    section_obj.updated_at = datetime.now(timezone.utc)
    session.add(section_obj)
    await mark_apertures_used(session, section_obj.media_id, [update_data.get("aperture_index")])
    await session.commit()
    await session.refresh(section_obj)
    return section_obj


@section_api.delete("/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete a section by its section_id."""
    section_obj = await section_or_404(session, section_id)
    await session.delete(section_obj)
    await session.commit()
    return None


@section_api.get("/sections/media/{media_id}", response_model=list[SectionResponse])
async def list_sections_by_media(
    media_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    relative_position: int | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections by media type and ID."""
    statement = select(SectionSQLModel).where(SectionSQLModel.media_id == media_id)
    if relative_position is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="relative_position is not supported")
    statement = statement.order_by(SectionSQLModel.section_number, SectionSQLModel.id)
    sections = await session.scalars(statement.offset(skip).limit(limit))
    return sections.all()


@section_api.post("/sections/{section_id}/image", response_model=FileObjectResponse)
async def image_put_url(
    section_id: str,
    storage_location: FileObjectRequest | None = Body(None, description="Storage location details for the image"),
    session: AsyncSession = Depends(get_async_session),
):
    """Generate a pre-signed URL for uploading an image for a specific section."""
    section = await session.scalars(
        select(SectionSQLModel)
        .where(
            SectionSQLModel.section_id == section_id,
        )
        .with_for_update()
    )
    section_obj = section.one_or_none()
    if section_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found",
        )
    if storage_location is None and section_obj.optical_image is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage location must be provided.",
        )
    if storage_location is None:
        storage_location = FileObject.model_validate(section_obj.optical_image)
    if any([val is None for key, val in storage_location.model_dump().items() if key != "server"]):
        cutting_session = await session.scalars(
            select(CuttingSessionSQLModel).where(
                CuttingSessionSQLModel.cutting_session_id == section_obj.cutting_session_id
            )
        )
        cutting_session_obj = cutting_session.one_or_none()
        if cutting_session_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cutting Session '{section_obj.cutting_session_id}' not found",
            )
        block = await session.scalars(
            select(BlockSQLModel).where(BlockSQLModel.block_id == cutting_session_obj.block_id)
        )
        block_obj = block.one_or_none()
        if block_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Block '{cutting_session_obj.block_id}' not found",
            )
        if block_obj.default_storage is not None:
            storage_location = storage_location.apply_defaults(block_obj.default_storage)

        if config.default_storage is not None:
            storage_location = storage_location.apply_defaults(config.default_storage)

    storage_location.key = storage_location.key.lstrip("/")

    if (
        section_obj.optical_image is not None
        and storage_location.model_dump(exclude={"expiration"}) != section_obj.optical_image
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Delete the existing image for section '{section_id}' before uploading a new one.",
        )

    match storage_location.protocol:
        case StorageProtocol.S3:
            client = boto3.client("s3", endpoint_url=storage_location.server)
            expiration = getattr(storage_location, "expiration", None) or 3600
            try:
                presigned_url = client.generate_presigned_url(
                    "put_object",
                    Params={"Bucket": storage_location.bucket, "Key": storage_location.key},
                    ExpiresIn=expiration,
                )
            except ClientError as e:
                logger.error(f"Error generating presigned URL: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error generating presigned URL for S3.",
                )
            response = FileObjectResponse(
                expiration=expiration,
                url=presigned_url,
                **storage_location.model_dump(exclude={"expiration"}),
            )
        case StorageProtocol.GCS:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Storage protocol '{storage_location.protocol}' is not yet implemented.",
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported storage protocol '{storage_location.protocol}'.",
            )

    if storage_location.model_dump(exclude={"expiration"}) != section_obj.optical_image:
        section_obj.optical_image = FileObject.model_validate(storage_location, from_attributes=True).model_dump()
        section_obj.updated_at = datetime.now(timezone.utc)
        session.add(section_obj)
        await session.commit()

    return response


@section_api.get("/sections/{section_id}/image", response_model=FileObjectResponse)
async def image_get_url(
    section_id: str,
    expiration: int = Query(3600, description="Expiration time in seconds for the presigned URL"),
    session: AsyncSession = Depends(get_async_session),
):
    """Generate a pre-signed URL for downloading an image for a specific section."""
    section = await session.scalars(
        select(SectionSQLModel).where(
            SectionSQLModel.section_id == section_id,
        )
    )
    section_obj = section.one_or_none()
    if section_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found",
        )
    if section_obj.optical_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No image found for section '{section_id}'",
        )

    storage_location = FileObject.model_validate(section_obj.optical_image)

    match storage_location.protocol:
        case StorageProtocol.S3:
            client = boto3.client("s3", endpoint_url=storage_location.server)
            try:
                presigned_url = client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": storage_location.bucket, "Key": storage_location.key},
                    ExpiresIn=expiration,
                )
            except ClientError as e:
                logger.error(f"Error generating presigned URL: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error generating presigned URL for S3.",
                )
            return FileObjectResponse(
                expiration=expiration,
                url=presigned_url,
                **storage_location.model_dump(),
            )
        case StorageProtocol.GCS:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Storage protocol '{storage_location.protocol}' is not yet implemented.",
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported storage protocol '{storage_location.protocol}'.",
            )


@section_api.delete("/sections/{section_id}/image", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    section_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete the image associated with a specific section."""
    section = await session.scalars(
        select(SectionSQLModel)
        .where(
            SectionSQLModel.section_id == section_id,
        )
        .with_for_update()
    )
    section_obj = section.one_or_none()
    if section_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section '{section_id}' not found",
        )
    if section_obj.optical_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No image found for section '{section_id}'",
        )

    storage_location = FileObject.model_validate(section_obj.optical_image)

    match storage_location.protocol:
        case StorageProtocol.S3:
            client = boto3.client("s3", endpoint_url=storage_location.server)
            try:
                client.delete_object(Bucket=storage_location.bucket, Key=storage_location.key)
            except ClientError as e:
                logger.error(f"Error deleting object from S3: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error deleting object from S3.",
                )
        case StorageProtocol.GCS:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Storage protocol '{storage_location.protocol}' is not yet implemented.",
            )
        case _:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported storage protocol '{storage_location.protocol}'.",
            )

    section_obj.optical_image = None
    section_obj.updated_at = datetime.now(timezone.utc)
    session.add(section_obj)
    await session.commit()
