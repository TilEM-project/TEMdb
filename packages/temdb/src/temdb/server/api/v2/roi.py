import logging
from collections.abc import Iterable
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from temdb.models import APIErrorResponse, ROIChildrenResponse, ROICreate, ROIResponse, ROIUpdate
from temdb.server.dependencies import get_async_session
from temdb.server.exception_handlers import BaseError
from temdb.server.sqlmodels import (
    AcquisitionSQLModel,
    AcquisitionTaskSQLModel,
    ROISQLModel,
    SectionSQLModel,
)

from ..utils import drop_null_keys, merge_extra
from .section import lock_substrate, section_or_404

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


def _vertex_fields(payload: dict) -> dict:
    """The payload's vertices, rotation_angle and buffer_size."""
    return {field: payload.get(field) for field in ("vertices", "rotation_angle", "buffer_size")}


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
    substrate_media_id: str | None = Query(None, description="Filter by substrate media ID"),
    aperture_index: int | None = Query(None, ge=0, description="Filter by layout aperture index"),
    is_parent_roi: bool | None = Query(None, description="Filter ROIs that are parents (have children)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """Retrieve a list of ROIs with optional filters and pagination."""
    statement = select(ROISQLModel)
    conditions = []
    if specimen_id or block_id or cutting_session_id:
        statement = statement.join(SectionSQLModel, SectionSQLModel.section_id == ROISQLModel.section_id)
    if specimen_id:
        conditions.append(SectionSQLModel.specimen_id == specimen_id)
    if block_id:
        conditions.append(SectionSQLModel.block_id == block_id)
    if cutting_session_id:
        conditions.append(SectionSQLModel.cutting_session_id == cutting_session_id)
    if section_id:
        conditions.append(ROISQLModel.section_id == section_id)
    if substrate_media_id:
        conditions.append(ROISQLModel.substrate_media_id == substrate_media_id)
    if aperture_index is not None:
        conditions.append(ROISQLModel.aperture_index == aperture_index)
    if is_parent_roi is not None:
        child = aliased(ROISQLModel)
        has_child = select(child.id).where(child.parent_roi_id == ROISQLModel.roi_id).exists()
        conditions.append(has_child if is_parent_roi else ~has_child)
    if conditions:
        statement = statement.where(and_(*conditions))
    rois = (await session.scalars(statement.order_by(ROISQLModel.roi_id).offset(skip).limit(limit))).all()
    parents_with_children = await _parents_with_children(session, (roi.roi_id for roi in rois))
    return [_to_response(roi, roi.roi_id in parents_with_children) for roi in rois]


async def _chain(session: AsyncSession, roi: ROISQLModel) -> list[ROISQLModel]:
    """The ROI and its ancestors, top-level ROI first."""
    chain = [roi]
    while chain[0].parent_roi_id:
        chain.insert(0, await session.scalar(select(ROISQLModel).where(ROISQLModel.roi_id == chain[0].parent_roi_id)))
    return chain


async def _parent(
    session: AsyncSession, section: SectionSQLModel, parent_created_at: datetime | None
) -> ROISQLModel | None:
    """The section's ROI created at parent_created_at."""
    if parent_created_at is None:
        return None
    parent = await session.scalar(
        select(ROISQLModel).where(
            ROISQLModel.section_id == section.section_id, ROISQLModel.created_at == parent_created_at
        )
    )
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No ROI created at {parent_created_at.isoformat()} on section '{section.section_id}'",
        )
    if len(await _chain(session, parent)) >= 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"ROI '{parent.roi_id}' is already 3 levels deep and cannot have sub-ROIs",
        )
    return parent


async def _number(session: AsyncSession, media_id: str, aperture_index: int | None) -> tuple[int, str]:
    """The next roi_number and roi_id on the aperture."""
    highest = await session.scalar(
        select(func.max(ROISQLModel.roi_number)).where(
            ROISQLModel.substrate_media_id == media_id, ROISQLModel.aperture_index.is_not_distinct_from(aperture_index)
        )
    )
    roi_number = (highest or 0) + 1
    if aperture_index is None:
        return roi_number, f"{media_id}.R{roi_number:04d}"
    return roi_number, f"{media_id}.A{aperture_index:04d}.R{roi_number:03d}"


async def _stored(
    session: AsyncSession, section: SectionSQLModel, roi_data: ROICreate, parent: ROISQLModel | None
) -> ROISQLModel | None:
    """The ROI already stored at this created_at on the aperture, or None."""
    stored = await session.scalar(
        select(ROISQLModel).where(
            ROISQLModel.substrate_media_id == section.media_id,
            ROISQLModel.aperture_index.is_not_distinct_from(section.aperture_index),
            ROISQLModel.created_at == roi_data.created_at,
        )
    )
    if stored is None:
        return None
    stored_fields = _vertex_fields(stored.roi_payload or {})
    sent_fields = _vertex_fields(roi_data.payload.model_dump(mode="json"))
    differing = [field for field in sent_fields if stored_fields[field] != sent_fields[field]]
    if stored.section_id != roi_data.section_id:
        differing.append("section_id")
    if stored.parent_roi_id != (parent.roi_id if parent else None):
        differing.append("parent_created_at")
    if differing:
        raise BaseError(
            f"ROI '{stored.roi_id}' has this created_at on this aperture with different {', '.join(differing)}",
            status_code=status.HTTP_409_CONFLICT,
            error_code="KEY_IN_USE",
        )
    return stored


async def _create(session: AsyncSession, roi_data: ROICreate) -> tuple[ROISQLModel, bool]:
    """Create the ROI, or return the stored one, and whether it was created."""
    section = await section_or_404(session, roi_data.section_id)
    await lock_substrate(session, section.media_id)
    parent = await _parent(session, section, roi_data.parent_created_at)
    stored = await _stored(session, section, roi_data, parent)
    if stored is not None:
        return stored, False
    roi_number, roi_id = await _number(session, section.media_id, section.aperture_index)
    roi = ROISQLModel(
        roi_id=roi_id,
        roi_number=roi_number,
        substrate_media_id=section.media_id,
        aperture_index=section.aperture_index,
        section_id=section.section_id,
        parent_roi_id=parent.roi_id if parent else None,
        roi_payload=roi_data.payload.model_dump(mode="json"),
        created_at=roi_data.created_at,
        updated_at=datetime.now(timezone.utc),
        extra=drop_null_keys(roi_data.extra),
    )
    session.add(roi)
    await session.flush()
    return roi, True


@roi_api.post(
    "/rois",
    response_model=ROIResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_200_OK: {"model": ROIResponse, "description": "The ROI was already stored"},
        status.HTTP_409_CONFLICT: {"model": APIErrorResponse, "description": "Same created_at, different ROI"},
    },
)
async def create_roi(roi_data: ROICreate, response: Response, session: AsyncSession = Depends(get_async_session)):
    """Create an ROI, or return the stored one with the same created_at."""
    roi, created = await _create(session, roi_data)
    if not created:
        response.status_code = status.HTTP_200_OK
    await session.commit()
    await session.refresh(roi)
    return _to_response(roi, await _has_children(session, roi.roi_id))


@roi_api.post(
    "/rois/batch",
    response_model=list[ROIResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create multiple ROIs in bulk",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": APIErrorResponse, "description": "Invalid input data"},
        status.HTTP_404_NOT_FOUND: {"model": APIErrorResponse, "description": "Section not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": APIErrorResponse, "description": "Internal server error"},
    },
)
async def create_rois_batch(
    rois_data: list[ROICreate],
    session: AsyncSession = Depends(get_async_session),
):
    """Create ROIs in order, storing none if one fails."""
    if not rois_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ROI data list cannot be empty.")
    rois = [(await _create(session, roi_data))[0] for roi_data in rois_data]
    await session.commit()
    for roi in rois:
        await session.refresh(roi)
    parents_with_children = await _parents_with_children(session, (roi.roi_id for roi in rois))
    return [_to_response(roi, roi.roi_id in parents_with_children) for roi in rois]


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
    roi = await session.scalar(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    if roi is None:
        raise HTTPException(status_code=404, detail=f"ROI with ID '{roi_id}' not found")
    hierarchy_path = [
        {"roi_id": item.roi_id, "section_id": item.section_id, "hierarchy_level": level}
        for level, item in enumerate(await _chain(session, roi), 1)
    ]
    return {"roi_id": roi_id, "hierarchy_path": hierarchy_path, "total_levels": len(hierarchy_path)}


async def _links(session: AsyncSession, roi_id: str) -> list[str]:
    """What refers to the ROI: its tasks, acquisitions and sub-ROIs."""
    tasks = await session.scalars(
        select(AcquisitionTaskSQLModel.task_id).where(AcquisitionTaskSQLModel.roi_id == roi_id)
    )
    acquisitions = await session.scalars(
        select(AcquisitionSQLModel.acquisition_id).where(AcquisitionSQLModel.roi_id == roi_id)
    )
    children = await session.scalars(select(ROISQLModel.roi_id).where(ROISQLModel.parent_roi_id == roi_id))
    return (
        [f"task {task}" for task in tasks]
        + [f"acquisition {acq}" for acq in acquisitions]
        + [f"sub-ROI {child}" for child in children]
    )


@roi_api.patch("/rois/{roi_id}", response_model=ROIResponse)
async def update_roi(
    roi_id: str,
    updated_fields: ROIUpdate = Body(...),
    session: AsyncSession = Depends(get_async_session),
):
    """Update an ROI's payload and extra."""
    roi_obj = await session.scalar(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    if roi_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ROI with ID '{roi_id}' not found")
    payload_update = updated_fields.payload.model_dump(mode="json", exclude_unset=True)
    if not payload_update and updated_fields.extra is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")
    stored_fields = _vertex_fields(roi_obj.roi_payload or {})
    changed = [
        field for field in stored_fields if field in payload_update and payload_update[field] != stored_fields[field]
    ]
    links = await _links(session, roi_obj.roi_id) if changed else []
    if links:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"ROI '{roi_id}' cannot change {', '.join(changed)} while {', '.join(links)} refer to it",
        )
    if payload_update:
        roi_obj.roi_payload = {**(roi_obj.roi_payload or {}), **payload_update}
    if updated_fields.extra is not None:
        roi_obj.extra = merge_extra(ROISQLModel.extra, updated_fields.extra)
    roi_obj.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(roi_obj)
    return _to_response(roi_obj, await _has_children(session, roi_obj.roi_id))


@roi_api.delete("/rois/{roi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_roi(roi_id: str, session: AsyncSession = Depends(get_async_session)):
    """Delete a specific ROI."""
    roi_result = await session.scalars(select(ROISQLModel).where(ROISQLModel.roi_id == roi_id))
    roi_obj = roi_result.one_or_none()
    if roi_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ROI with ID '{roi_id}' not found")
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


@roi_api.get("/rois/{roi_id}/children", response_model=ROIChildrenResponse)
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
    total_children = await session.scalar(
        select(func.count()).select_from(ROISQLModel).where(ROISQLModel.parent_roi_id == roi_id)
    )
    more_results = skip + limit < total_children
    parents_with_children = await _parents_with_children(session, (child.roi_id for child in children_list))
    return {
        "children": [_to_response(child, child.roi_id in parents_with_children) for child in children_list],
        "metadata": {"skip": skip, "limit": limit, "total_children": total_children, "has_more": more_results},
    }
