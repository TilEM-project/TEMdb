import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import APIErrorResponse, ROICreate, ROIResponse, ROIUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.sqlmodels import (
    AcquisitionSQLModel,
    AcquisitionTaskSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SubstrateSQLModel,
)

roi_api = APIRouter(
    tags=["ROIs"],
)

logger = logging.getLogger(__name__)


def _roi_payload(roi: ROISQLModel, parent_internal_id: int | None = None) -> dict:
    base = dict(roi.roi_payload or {})
    base.update(
        {
            "_id": str(roi.id),
            "roi_id": roi.roi_id,
            "roi_number": roi.roi_number,
            "section_id": roi.section_id,
            "block_id": roi.block_id,
            "specimen_id": roi.specimen_id,
            "substrate_media_id": roi.substrate_media_id,
            "hierarchy_level": roi.hierarchy_level,
            "section_number": roi.section_number,
            "updated_at": roi.updated_at,
        }
    )
    base["parent_roi_ref"] = {"id": str(parent_internal_id)} if parent_internal_id is not None else None
    return base


@roi_api.get("/rois")
async def list_rois(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    cutting_session_id: str | None = Query(None, description="Filter by human-readable Cutting Session ID"),
    section_id: str | None = Query(None, description="Filter by human-readable Section ID"),
    is_parent_roi: bool | None = Query(None, description="Filter ROIs that are parents (have children)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of ROIs with optional filters and pagination."""
    statement = select(ROISQLModel)
    conditions = []
    if specimen_id:
        conditions.append(ROISQLModel.specimen_id == specimen_id)
    if block_id:
        conditions.append(ROISQLModel.block_id == block_id)
    if cutting_session_id:
        sections = await session.exec(
            select(SectionSQLModel.section_id).where(SectionSQLModel.cutting_session_id == cutting_session_id)
        )
        section_ids = [item for item in sections]
        if not section_ids:
            return []
        conditions.append(ROISQLModel.section_id.in_(section_ids))
    if section_id:
        conditions.append(ROISQLModel.section_id == section_id)
    if conditions:
        statement = statement.where(and_(*conditions))
    rois = (await session.exec(statement.offset(skip).limit(limit))).all()
    return [_roi_payload(roi, None) for roi in rois]


@roi_api.post("/rois", status_code=status.HTTP_201_CREATED)
async def create_roi(roi_data: ROICreate, session: AsyncSession = Depends(get_async_session)):
    """Create a new ROI with hierarchical ID generation."""
    section = await session.exec(select(SectionSQLModel).where(SectionSQLModel.section_id == roi_data.section_id))
    section_obj = section.one_or_none()
    if section_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section with ID '{roi_data.section_id}' not found",
        )
    substrate = await session.exec(
        select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == roi_data.substrate_media_id)
    )
    if substrate.one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{roi_data.substrate_media_id}' not found",
        )
    parent_roi = None
    hierarchy_level = 1
    if roi_data.parent_roi_id:
        parent_result = await session.exec(select(ROISQLModel).where(ROISQLModel.roi_id == roi_data.parent_roi_id))
        parent_roi = parent_result.one_or_none()
        if parent_roi is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent ROI with ID '{roi_data.parent_roi_id}' not found",
            )
        hierarchy_level = parent_roi.hierarchy_level + 1
    roi_id = ROISQLModel.generate_roi_id(
        specimen_id=roi_data.specimen_id,
        block_id=roi_data.block_id,
        section_id=roi_data.section_id,
        substrate_media_id=roi_data.substrate_media_id,
        roi_number=roi_data.roi_number,
        parent_roi_id=roi_data.parent_roi_id,
    )
    existing_roi = await session.exec(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    if existing_roi.one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"ROI with ID '{roi_id}' already exists")

    payload = roi_data.model_dump(mode="json")
    for key in (
        "roi_number",
        "section_id",
        "specimen_id",
        "block_id",
        "substrate_media_id",
        "parent_roi_id",
        "section_number",
    ):
        payload.pop(key, None)
    new_roi = ROISQLModel(
        roi_id=roi_id,
        roi_number=roi_data.roi_number,
        section_id=roi_data.section_id,
        block_id=roi_data.block_id,
        specimen_id=roi_data.specimen_id,
        substrate_media_id=roi_data.substrate_media_id,
        hierarchy_level=hierarchy_level,
        parent_roi_id=roi_data.parent_roi_id,
        section_number=roi_data.section_number,
        roi_payload=payload,
        updated_at=datetime.now(timezone.utc),
    )
    session.add(new_roi)
    await session.commit()
    await session.refresh(new_roi)
    return _roi_payload(new_roi, parent_roi.id if parent_roi else None)


@roi_api.post(
    "/rois/batch",
    response_model=list[ROIResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create multiple ROIs in bulk",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": APIErrorResponse, "description": "Invalid input data"},
        status.HTTP_404_NOT_FOUND: {"model": APIErrorResponse, "description": "Parent section not found"},
        status.HTTP_409_CONFLICT: {"model": APIErrorResponse, "description": "Duplicate ROI ID"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": APIErrorResponse, "description": "Internal server error"},
    },
)
async def create_rois_batch(
    rois_data: list[ROICreate],
    session: AsyncSession = Depends(get_async_session),
):
    """Creates multiple ROI documents from a list with hierarchical ID generation."""
    if not rois_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ROI data list cannot be empty.")

    section_cache: dict[str, SectionSQLModel] = {}
    seen_roi_ids: set[str] = set()
    rois_to_insert: list[ROISQLModel] = []

    for index, roi_create in enumerate(rois_data):
        section_id = roi_create.section_id
        if section_id not in section_cache:
            section = await session.exec(select(SectionSQLModel).where(SectionSQLModel.section_id == section_id))
            section_obj = section.one_or_none()
            if section_obj is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Section '{section_id}' not found for ROI item {index}.",
                )
            section_cache[section_id] = section_obj
        section_obj = section_cache[section_id]

        substrate = await session.exec(
            select(SubstrateSQLModel).where(SubstrateSQLModel.media_id == roi_create.substrate_media_id)
        )
        if substrate.one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Substrate with media_id '{roi_create.substrate_media_id}' not found for ROI item {index}.",
            )

        roi_id = ROISQLModel.generate_roi_id(
            specimen_id=roi_create.specimen_id,
            block_id=roi_create.block_id,
            section_id=roi_create.section_id,
            substrate_media_id=roi_create.substrate_media_id,
            roi_number=roi_create.roi_number,
            parent_roi_id=roi_create.parent_roi_id,
        )
        if roi_id in seen_roi_ids:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="duplicate ROI IDs in batch")
        seen_roi_ids.add(roi_id)
        hierarchy_level = ROISQLModel.parse_hierarchy_level(roi_id)
        payload = roi_create.model_dump(mode="json")
        for key in (
            "roi_number",
            "section_id",
            "specimen_id",
            "block_id",
            "substrate_media_id",
            "parent_roi_id",
            "section_number",
        ):
            payload.pop(key, None)
        rois_to_insert.append(
            ROISQLModel(
                roi_id=roi_id,
                roi_number=roi_create.roi_number,
                section_id=section_obj.section_id,
                block_id=section_obj.block_id,
                specimen_id=section_obj.specimen_id,
                substrate_media_id=roi_create.substrate_media_id,
                hierarchy_level=hierarchy_level,
                parent_roi_id=roi_create.parent_roi_id,
                section_number=roi_create.section_number,
                roi_payload=payload,
                updated_at=datetime.now(timezone.utc),
            )
        )

    session.add_all(rois_to_insert)
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"duplicate ROI IDs: {error.orig}") from error
    for roi in rois_to_insert:
        await session.refresh(roi)
    parent_map = {roi.roi_id: roi.id for roi in rois_to_insert}
    return [
        _roi_payload(roi, parent_map.get(roi.parent_roi_id) if roi.parent_roi_id else None) for roi in rois_to_insert
    ]


@roi_api.get("/rois/{roi_id}")
async def get_roi(roi_id: str, session: AsyncSession = Depends(get_async_session)):
    """Retrieve a specific ROI by its human-readable integer ID."""
    roi = await session.exec(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    roi_obj = roi.one_or_none()
    if roi_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ROI with ID '{roi_id}' not found")
    parent = None
    if roi_obj.parent_roi_id:
        parent_result = await session.exec(select(ROISQLModel).where(ROISQLModel.roi_id == roi_obj.parent_roi_id))
        parent = parent_result.one_or_none()
    return _roi_payload(roi_obj, parent.id if parent else None)


@roi_api.get("/rois/{roi_id}/hierarchy", response_model=dict)
async def get_roi_hierarchy(roi_id: str, session: AsyncSession = Depends(get_async_session)):
    """Get the full hierarchy path for an ROI."""
    roi_result = await session.exec(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    current = roi_result.one_or_none()
    if current is None:
        raise HTTPException(status_code=404, detail=f"ROI with ID '{roi_id}' not found")
    hierarchy_path = []
    while current:
        hierarchy_path.insert(
            0,
            {"roi_id": current.roi_id, "hierarchy_level": current.hierarchy_level, "section_id": current.section_id},
        )
        if current.parent_roi_id:
            parent_result = await session.exec(select(ROISQLModel).where(ROISQLModel.roi_id == current.parent_roi_id))
            current = parent_result.one_or_none()
        else:
            current = None
    return {"roi_id": roi_id, "hierarchy_path": hierarchy_path, "total_levels": len(hierarchy_path)}


@roi_api.patch("/rois/{roi_id}")
async def update_roi(
    roi_id: str,
    updated_fields: ROIUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details (attributes from ROIBase) of a specific ROI."""
    roi_result = await session.exec(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    roi_obj = roi_result.one_or_none()
    if roi_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ROI with ID '{roi_id}' not found")
    update_data = updated_fields.model_dump(mode="json", exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    payload = dict(roi_obj.roi_payload or {})
    payload.update(update_data)
    roi_obj.roi_payload = payload
    roi_obj.updated_at = datetime.now(timezone.utc)
    session.add(roi_obj)
    await session.commit()
    await session.refresh(roi_obj)
    parent = None
    if roi_obj.parent_roi_id:
        parent_result = await session.exec(select(ROISQLModel).where(ROISQLModel.roi_id == roi_obj.parent_roi_id))
        parent = parent_result.one_or_none()
    return _roi_payload(roi_obj, parent.id if parent else None)


@roi_api.delete("/rois/{roi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_roi(roi_id: str, session: AsyncSession = Depends(get_async_session)):
    """Delete a specific ROI."""
    roi_result = await session.exec(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    roi_obj = roi_result.one_or_none()
    if roi_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ROI with ID '{roi_id}' not found")
    child_rois_count = await session.exec(select(ROISQLModel).where(ROISQLModel.parent_roi_id == roi_id))
    if child_rois_count.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete ROI '{roi_id}' as it has child ROIs",
        )
    task_count = await session.exec(select(AcquisitionTaskSQLModel).where(AcquisitionTaskSQLModel.roi_id == roi_id))
    if task_count.first() is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete ROI '{roi_id}' as it has associated Acquisition Tasks.",
        )
    acq_count = await session.exec(select(AcquisitionSQLModel).where(AcquisitionSQLModel.roi_id == roi_id))
    if acq_count.first() is not None:
        raise HTTPException(status_code=400, detail=f"Cannot delete ROI '{roi_id}' as it has associated Acquisitions.")
    await session.delete(roi_obj)
    await session.commit()
    return None


@roi_api.get("/sections/{section_id}/rois")
async def list_section_rois(
    section_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve ROIs associated with a specific section using its human-readable ID."""
    rois = await session.exec(
        select(ROISQLModel)
        .where(ROISQLModel.section_id == section_id)
        .order_by(ROISQLModel.roi_id)
        .offset(skip)
        .limit(limit)
    )
    roi_items = rois.all()
    if not roi_items:
        section = await session.exec(select(SectionSQLModel).where(SectionSQLModel.section_id == section_id))
        if section.one_or_none() is None:
            raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")
    id_map = {roi.roi_id: roi.id for roi in roi_items}
    return [_roi_payload(roi, id_map.get(roi.parent_roi_id) if roi.parent_roi_id else None) for roi in roi_items]


@roi_api.get("/rois/{roi_id}/children", response_model=dict)
async def get_child_rois(
    roi_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve child ROIs for a given parent ROI using the parent's hierarchical ID."""
    parent_roi = await session.exec(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    parent_obj = parent_roi.one_or_none()
    if parent_obj is None:
        raise HTTPException(status_code=404, detail=f"Parent ROI with ID '{roi_id}' not found")
    children = await session.exec(
        select(ROISQLModel)
        .where(ROISQLModel.parent_roi_id == roi_id)
        .order_by(ROISQLModel.roi_id)
        .offset(skip)
        .limit(limit)
    )
    children_list = children.all()
    total_children = len((await session.exec(select(ROISQLModel).where(ROISQLModel.parent_roi_id == roi_id))).all())
    more_results = skip + limit < total_children
    return {
        "children": [_roi_payload(child, parent_obj.id) for child in children_list],
        "metadata": {"skip": skip, "limit": limit, "total_children": total_children, "has_more": more_results},
    }
