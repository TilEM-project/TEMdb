from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import SubstrateCreate, SubstrateUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import SectionSQLModel, SubstrateSQLModel

substrate_api = APIRouter(
    tags=["Substrates"],
)


def _sql_substrate_payload(substrate: SubstrateSQLModel) -> dict:
    return {
        "_id": str(substrate.id),
        "media_id": substrate.media_id,
        "media_type": substrate.media_type,
        "uid": substrate.uid,
        "status": substrate.status,
        "refpoint": substrate.refpoint,
        "refpoint_world": substrate.refpoint_world,
        "source_path": substrate.source_path,
        "metadata": substrate.metadata_json,
        "apertures": substrate.apertures,
        "created_at": substrate.created_at,
        "updated_at": substrate.updated_at,
    }


def _sql_section_payload(section: SectionSQLModel, substrate_internal_id: int | None = None) -> dict:
    payload = {
        "_id": str(section.id),
        "section_id": section.section_id,
        "section_number": section.section_number,
        "timestamp": section.timestamp,
        "cutting_session_id": section.cutting_session_id,
        "block_id": section.block_id,
        "specimen_id": section.specimen_id,
        "media_id": section.media_id,
        "optical_image": section.optical_image,
        "aperture_uid": section.aperture_uid,
        "aperture_index": section.aperture_index,
        "barcode": section.barcode,
        "section_metrics": section.section_metrics,
        "created_at": section.created_at,
        "updated_at": section.updated_at,
    }
    if substrate_internal_id is not None:
        payload["substrate_ref"] = {"id": str(substrate_internal_id)}
    return payload


def _to_json_compatible(value):
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return jsonable_encoder(value)


@substrate_api.get("/substrates")
async def list_substrates(
    media_type: str | None = Query(None, description="Filter by substrate media type (e.g., 'wafer', 'tape')"),
    status: str | None = Query(None, description="Filter by substrate status (e.g., 'new', 'used')"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of records to return"),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of substrates with optional filters and pagination."""
    statement = select(SubstrateSQLModel)
    if media_type:
        statement = statement.where(SubstrateSQLModel.media_type == media_type)
    if status:
        statement = statement.where(SubstrateSQLModel.status == status)
    substrates = (await session.exec(statement.offset(skip).limit(limit))).all()
    return [_sql_substrate_payload(substrate) for substrate in substrates]


@substrate_api.post("/substrates", status_code=status.HTTP_201_CREATED)
async def create_substrate(
    substrate_data: SubstrateCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create a new substrate."""
    existing_substrate = await session.exec(
        select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == substrate_data.media_id)
    )
    if existing_substrate.one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Substrate with media_id '{substrate_data.media_id}' already exists.",
        )
    new_substrate = SubstrateSQLModel(
        media_id=substrate_data.media_id,
        media_type=substrate_data.media_type,
        uid=substrate_data.uid,
        status=substrate_data.status,
        refpoint=(
            substrate_data.refpoint.model_dump(mode="json")
            if getattr(substrate_data, "refpoint", None) is not None
            else None
        ),
        refpoint_world=(
            substrate_data.refpoint_world.model_dump(mode="json")
            if getattr(substrate_data, "refpoint_world", None) is not None
            else None
        ),
        source_path=substrate_data.source_path,
        metadata_json=(
            substrate_data.metadata.model_dump(mode="json")
            if getattr(substrate_data, "metadata", None) is not None
            else None
        ),
        apertures=(
            [ap.model_dump(mode="json") for ap in substrate_data.apertures]
            if getattr(substrate_data, "apertures", None) is not None
            else None
        ),
        created_at=datetime.now(timezone.utc),
    )
    session.add(new_substrate)
    await session.commit()
    await session.refresh(new_substrate)
    return _sql_substrate_payload(new_substrate)


@substrate_api.get("/substrates/{media_id}")
async def get_substrate(media_id: str, session: AsyncSession = Depends(get_async_session)):
    """Retrieve a specific substrate by its unique media_id."""
    substrate = await session.exec(select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id))
    substrate_obj = substrate.one_or_none()
    if substrate_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    return _sql_substrate_payload(substrate_obj)


@substrate_api.patch("/substrates/{media_id}")
async def update_substrate(
    media_id: str,
    updated_fields: SubstrateUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details of a specific substrate identified by media_id."""
    substrate = await session.exec(select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id))
    substrate_obj = substrate.one_or_none()
    if substrate_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    needs_save = False
    if "uid" in update_data and substrate_obj.uid != update_data["uid"]:
        substrate_obj.uid = update_data["uid"]
        needs_save = True
    if "status" in update_data and substrate_obj.status != update_data["status"]:
        substrate_obj.status = update_data["status"]
        needs_save = True
    if "source_path" in update_data and substrate_obj.source_path != update_data["source_path"]:
        substrate_obj.source_path = update_data["source_path"]
        needs_save = True
    if "refpoint" in update_data:
        refpoint = _to_json_compatible(update_data["refpoint"])
        if substrate_obj.refpoint != refpoint:
            substrate_obj.refpoint = refpoint
            needs_save = True
    if "refpoint_world" in update_data:
        refpoint_world = _to_json_compatible(update_data["refpoint_world"])
        if substrate_obj.refpoint_world != refpoint_world:
            substrate_obj.refpoint_world = refpoint_world
            needs_save = True
    if "metadata" in update_data:
        metadata_value = _to_json_compatible(update_data["metadata"])
        if substrate_obj.metadata_json != metadata_value:
            substrate_obj.metadata_json = metadata_value
            needs_save = True
    if "apertures" in update_data:
        apertures_value = _to_json_compatible(update_data["apertures"])
        if substrate_obj.apertures != apertures_value:
            substrate_obj.apertures = apertures_value
            needs_save = True

    if needs_save:
        substrate_obj.updated_at = datetime.now(timezone.utc)
        session.add(substrate_obj)
        await session.commit()
        await session.refresh(substrate_obj)
    return _sql_substrate_payload(substrate_obj)


@substrate_api.delete("/substrates/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_substrate(media_id: str, session: AsyncSession = Depends(get_async_session)):
    """Delete a specific substrate by its media_id."""
    substrate = await session.exec(select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id))
    substrate_obj = substrate.one_or_none()
    if substrate_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    section_count = await session.exec(select(SectionSQLModel).where(SectionSQLModel.media_id == media_id))
    if len(section_count.all()) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete substrate '{media_id}' as it has associated sections.",
        )
    await session.delete(substrate_obj)
    await session.commit()
    return None


@substrate_api.get("/substrates/{media_id}/sections")
async def get_substrate_sections(
    media_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve sections associated with a specific substrate, identified by media_id."""
    substrate = await session.exec(select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == media_id))
    substrate_obj = substrate.one_or_none()
    if substrate_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{media_id}' not found",
        )
    sections = await session.exec(
        select(SectionSQLModel)
        .where(SectionSQLModel.media_id == media_id)
        .order_by(SectionSQLModel.section_number)
        .offset(skip)
        .limit(limit)
    )
    return [_sql_section_payload(section, substrate_obj.id) for section in sections.all()]
