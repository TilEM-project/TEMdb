import logging
from collections.abc import Iterable
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


async def _has_children(session: AsyncSession, roi_id: str) -> bool:
    """Whether any ROI references `roi_id` as its parent."""
    result = await session.scalars(select(ROISQLModel.id).where(ROISQLModel.parent_roi_id == roi_id).limit(1))
    return result.first() is not None


async def _parents_with_children(session: AsyncSession, roi_ids: Iterable[str]) -> set[str]:
    """Batch version of `_has_children`: which of `roi_ids` have at least one child."""
    candidate_ids = [roi_id for roi_id in roi_ids if roi_id]
    if not candidate_ids:
        return set()
    result = await session.scalars(
        select(ROISQLModel.parent_roi_id).where(ROISQLModel.parent_roi_id.in_(candidate_ids)).distinct()
    )
    return {parent_id for parent_id in result if parent_id is not None}


def _to_response(roi: ROISQLModel, is_parent: bool = False) -> ROIResponse:
    response = ROIResponse.model_validate(roi)
    response.is_parent = is_parent
    return response


@roi_api.get("/rois", response_model=list[ROIResponse])
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
        sections = await session.scalars(
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
    rois = (await session.scalars(statement.offset(skip).limit(limit))).all()
    parents_with_children = await _parents_with_children(session, (roi.roi_id for roi in rois))
    return [_to_response(roi, roi.roi_id in parents_with_children) for roi in rois]


@roi_api.post("/rois", response_model=ROIResponse, status_code=status.HTTP_201_CREATED)
async def create_roi(roi_data: ROICreate, session: AsyncSession = Depends(get_async_session)):
    """Create a new ROI with hierarchical ID generation."""
    section = await session.scalars(select(SectionSQLModel).where(SectionSQLModel.section_id == roi_data.section_id))
    section_obj = section.one_or_none()
    if section_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section with ID '{roi_data.section_id}' not found",
        )
    substrate = await session.scalars(
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
        parent_result = await session.scalars(select(ROISQLModel).where(ROISQLModel.roi_id == roi_data.parent_roi_id))
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
    existing_roi = await session.scalars(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    if existing_roi.one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"ROI with ID '{roi_id}' already exists")

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
        roi_payload=roi_data.payload.model_dump(mode="json"),
        created_at=roi_data.created_at or datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(new_roi)
    await session.commit()
    await session.refresh(new_roi)
    return _to_response(new_roi, is_parent=False)


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
            section = await session.scalars(select(SectionSQLModel).where(SectionSQLModel.section_id == section_id))
            section_obj = section.one_or_none()
            if section_obj is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Section '{section_id}' not found for ROI item {index}.",
                )
            section_cache[section_id] = section_obj
        section_obj = section_cache[section_id]

        substrate = await session.scalars(
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
                roi_payload=roi_create.payload.model_dump(mode="json"),
                created_at=roi_create.created_at or datetime.now(timezone.utc),
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
    # Newly inserted ROIs may be parents of each other (child created before parent in the
    # same batch is impossible given FK ordering, but a batch may contain a parent whose
    # child is also in the batch), so derive is_parent from the batch's own parent links.
    parent_ids_in_batch = {roi.parent_roi_id for roi in rois_to_insert if roi.parent_roi_id}
    return [_to_response(roi, roi.roi_id in parent_ids_in_batch) for roi in rois_to_insert]


@roi_api.get("/rois/{roi_id}", response_model=ROIResponse)
async def get_roi(roi_id: str, session: AsyncSession = Depends(get_async_session)):
    """Retrieve a specific ROI by its human-readable integer ID."""
    roi = await session.scalars(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    roi_obj = roi.one_or_none()
    if roi_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ROI with ID '{roi_id}' not found")
    is_parent = await _has_children(session, roi_obj.roi_id)
    return _to_response(roi_obj, is_parent)


@roi_api.get("/rois/{roi_id}/hierarchy", response_model=dict)
async def get_roi_hierarchy(roi_id: str, session: AsyncSession = Depends(get_async_session)):
    """Get the full hierarchy path for an ROI."""
    roi_result = await session.scalars(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
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
            parent_result = await session.scalars(
                select(ROISQLModel).where(ROISQLModel.roi_id == current.parent_roi_id)
            )
            current = parent_result.one_or_none()
        else:
            current = None
    return {"roi_id": roi_id, "hierarchy_path": hierarchy_path, "total_levels": len(hierarchy_path)}


@roi_api.patch("/rois/{roi_id}", response_model=ROIResponse)
async def update_roi(
    roi_id: str,
    updated_fields: ROIUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update details (attributes from ROIPayload) of a specific ROI."""
    roi_result = await session.scalars(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    roi_obj = roi_result.one_or_none()
    if roi_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ROI with ID '{roi_id}' not found")
    update_data = updated_fields.payload.model_dump(mode="json", exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    payload = dict(roi_obj.roi_payload or {})
    payload.update(update_data)
    roi_obj.roi_payload = payload
    roi_obj.updated_at = datetime.now(timezone.utc)
    session.add(roi_obj)
    await session.commit()
    await session.refresh(roi_obj)
    is_parent = await _has_children(session, roi_obj.roi_id)
    return _to_response(roi_obj, is_parent)


@roi_api.delete("/rois/{roi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_roi(roi_id: str, session: AsyncSession = Depends(get_async_session)):
    """Delete a specific ROI."""
    roi_result = await session.scalars(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    roi_obj = roi_result.one_or_none()
    if roi_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ROI with ID '{roi_id}' not found")
    child_rois_count = await session.scalars(select(ROISQLModel).where(ROISQLModel.parent_roi_id == roi_id))
    if child_rois_count.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete ROI '{roi_id}' as it has child ROIs",
        )
    task_count = await session.scalars(select(AcquisitionTaskSQLModel).where(AcquisitionTaskSQLModel.roi_id == roi_id))
    if task_count.first() is not None:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete ROI '{roi_id}' as it has associated Acquisition Tasks.",
        )
    acq_count = await session.scalars(select(AcquisitionSQLModel).where(AcquisitionSQLModel.roi_id == roi_id))
    if acq_count.first() is not None:
        raise HTTPException(status_code=400, detail=f"Cannot delete ROI '{roi_id}' as it has associated Acquisitions.")
    await session.delete(roi_obj)
    await session.commit()
    return None


@roi_api.get("/sections/{section_id}/rois", response_model=list[ROIResponse])
async def list_section_rois(
    section_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve ROIs associated with a specific section using its human-readable ID."""
    rois = await session.scalars(
        select(ROISQLModel)
        .where(ROISQLModel.section_id == section_id)
        .order_by(ROISQLModel.roi_id)
        .offset(skip)
        .limit(limit)
    )
    roi_items = rois.all()
    if not roi_items:
        section = await session.scalars(select(SectionSQLModel).where(SectionSQLModel.section_id == section_id))
        if section.one_or_none() is None:
            raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")
    parents_with_children = await _parents_with_children(session, (roi.roi_id for roi in roi_items))
    return [_to_response(roi, roi.roi_id in parents_with_children) for roi in roi_items]


@roi_api.get("/rois/{roi_id}/children", response_model=dict)
async def get_child_rois(
    roi_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve child ROIs for a given parent ROI using the parent's hierarchical ID."""
    parent_roi = await session.scalars(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    parent_obj = parent_roi.one_or_none()
    if parent_obj is None:
        raise HTTPException(status_code=404, detail=f"Parent ROI with ID '{roi_id}' not found")
    children = await session.scalars(
        select(ROISQLModel)
        .where(ROISQLModel.parent_roi_id == roi_id)
        .order_by(ROISQLModel.roi_id)
        .offset(skip)
        .limit(limit)
    )
    children_list = children.all()
    total_children = len((await session.scalars(select(ROISQLModel).where(ROISQLModel.parent_roi_id == roi_id))).all())
    more_results = skip + limit < total_children
    parents_with_children = await _parents_with_children(session, (child.roi_id for child in children_list))
    return {
        "children": [_to_response(child, child.roi_id in parents_with_children) for child in children_list],
        "metadata": {"skip": skip, "limit": limit, "total_children": total_children, "has_more": more_results},
    }
