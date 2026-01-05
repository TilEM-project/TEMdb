import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Body, HTTPException, Query, status
from pymongo.errors import BulkWriteError
from temdb.models import APIErrorResponse, ROICreate, ROIResponse, ROIUpdate
from temdb.server.documents import (
    AcquisitionDocument as Acquisition,
)
from temdb.server.documents import (
    AcquisitionTaskDocument as AcquisitionTask,
)
from temdb.server.documents import (
    ROIDocument as ROI,
)
from temdb.server.documents import (
    SectionDocument as Section,
)
from temdb.server.documents import (
    SubstrateDocument as Substrate,
)

roi_api = APIRouter(
    tags=["ROIs"],
)

logger = logging.getLogger(__name__)


@roi_api.get("/rois", response_model=list[ROI])
async def list_rois(
    specimen_id: str | None = Query(None, description="Filter by human-readable Specimen ID"),
    block_id: str | None = Query(None, description="Filter by human-readable Block ID"),
    cutting_session_id: str | None = Query(None, description="Filter by human-readable Cutting Session ID"),
    section_id: str | None = Query(None, description="Filter by human-readable Section ID"),
    is_parent_roi: bool | None = Query(None, description="Filter ROIs that are parents (have children)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve a list of ROIs with optional filters and pagination."""
    query_filter = {}
    if specimen_id:
        query_filter["specimen_id"] = specimen_id
    if block_id:
        query_filter["block_id"] = block_id
    if cutting_session_id:
        sections = await Section.find(Section.cutting_session_id == cutting_session_id).to_list()
        section_ids = [s.section_id for s in sections]
        if not section_ids:
            return []
        query_filter["section_id"] = {"$in": section_ids}
    if section_id:
        query_filter["section_id"] = section_id
    if is_parent_roi is not None:
        pass

    return await ROI.find(query_filter, fetch_links=True).skip(skip).limit(limit).to_list()


@roi_api.post("/rois", response_model=ROI, status_code=status.HTTP_201_CREATED)
async def create_roi(roi_data: ROICreate):
    """Create a new ROI with hierarchical ID generation."""
    section = await Section.find_one(Section.section_id == roi_data.section_id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section with ID '{roi_data.section_id}' not found",
        )

    substrate = await Substrate.find_one(Substrate.media_id == roi_data.substrate_media_id)
    if not substrate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Substrate with media_id '{roi_data.substrate_media_id}' not found",
        )

    parent_roi = None
    parent_roi_ref_id = None
    hierarchy_level = 1

    if roi_data.parent_roi_id:
        parent_roi = await ROI.find_one(ROI.roi_id == roi_data.parent_roi_id)
        if not parent_roi:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent ROI with ID '{roi_data.parent_roi_id}' not found",
            )
        parent_roi_ref_id = parent_roi.id
        hierarchy_level = parent_roi.hierarchy_level + 1

    roi_id = ROI.generate_roi_id(
        specimen_id=roi_data.specimen_id,
        block_id=roi_data.block_id,
        section_id=roi_data.section_id,
        substrate_media_id=roi_data.substrate_media_id,
        roi_number=roi_data.roi_number,
        parent_roi_id=roi_data.parent_roi_id,
    )

    existing_roi = await ROI.find_one(ROI.roi_id == roi_id)
    if existing_roi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ROI with ID '{roi_id}' already exists",
        )

    roi_payload = roi_data.model_dump(exclude={"section_id", "parent_roi_id"})

    new_roi = ROI(
        **roi_payload,
        roi_id=roi_id,
        hierarchy_level=hierarchy_level,
        section_ref=section.id,
        parent_roi_ref=parent_roi_ref_id,
        section_id=section.section_id,
        updated_at=datetime.now(timezone.utc),
    )

    await new_roi.insert()
    created_roi = await ROI.get(new_roi.id, fetch_links=True)
    return created_roi


@roi_api.post(
    "/rois/batch",
    response_model=list[ROIResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create multiple ROIs in bulk",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": APIErrorResponse,
            "description": "Invalid input data",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": APIErrorResponse,
            "description": "Parent section not found",
        },
        status.HTTP_409_CONFLICT: {
            "model": APIErrorResponse,
            "description": "Duplicate ROI ID",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": APIErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def create_rois_batch(rois_data: list[ROICreate]):
    """Creates multiple ROI documents from a list with hierarchical ID generation."""
    if not rois_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ROI data list cannot be empty.",
        )

    rois_to_insert = []
    parent_section_cache = {}
    substrate_cache = {}

    for i, roi_create in enumerate(rois_data):
        section_id = roi_create.section_id
        if section_id not in parent_section_cache:
            section = await Section.find_one(Section.section_id == section_id)
            if not section:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Section '{section_id}' not found for ROI item {i}.",
                )
            parent_section_cache[section_id] = section
        section = parent_section_cache[section_id]

        substrate_media_id = roi_create.substrate_media_id
        if substrate_media_id not in substrate_cache:
            substrate = await Substrate.find_one(Substrate.media_id == substrate_media_id)
            if not substrate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Substrate with media_id '{substrate_media_id}' not found for ROI item {i}.",
                )
            substrate_cache[substrate_media_id] = substrate

        roi_id = ROI.generate_roi_id(
            specimen_id=roi_create.specimen_id,
            block_id=roi_create.block_id,
            section_id=roi_create.section_id,
            substrate_media_id=roi_create.substrate_media_id,
            roi_number=roi_create.roi_number,
            parent_roi_id=roi_create.parent_roi_id,
        )

        hierarchy_level = ROI.parse_hierarchy_level(roi_id)

        roi_doc_data = roi_create.model_dump(exclude={"section_id", "parent_roi_id"})
        roi_doc_data.update(
            {
                "roi_id": roi_id,
                "hierarchy_level": hierarchy_level,
                "section_ref": section.id,
                "section_id": section.section_id,
                "block_id": section.block_id,
                "specimen_id": section.specimen_id,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        roi_doc = ROI(**roi_doc_data)
        rois_to_insert.append(roi_doc)

    try:
        await ROI.insert_many(rois_to_insert)
        return rois_to_insert
    except BulkWriteError as e:
        logger.error(f"BulkWriteError during ROI batch insert: {e.details}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Bulk insert failed. Check for duplicate ROI IDs within the batch "
                f"or against existing data. Details: {e.details.get('writeErrors')}"
            ),
        )
    except Exception as e:
        logger.exception("Unexpected error during ROI batch insert.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An internal error occurred during bulk ROI creation: {e}",
        )


@roi_api.get("/rois/{roi_id}", response_model=ROI)
async def get_roi(roi_id: str):
    """Retrieve a specific ROI by its human-readable integer ID."""
    roi = await ROI.find_one(ROI.roi_id == roi_id, fetch_links=True)
    if not roi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ROI with ID '{roi_id}' not found",
        )
    return roi


@roi_api.get("/rois/{roi_id}/hierarchy", response_model=dict)
async def get_roi_hierarchy(roi_id: str):
    """Get the full hierarchy path for an ROI."""
    roi = await ROI.find_one(ROI.roi_id == roi_id, fetch_links=True)
    if not roi:
        raise HTTPException(status_code=404, detail=f"ROI with ID '{roi_id}' not found")

    hierarchy_path = []
    current_roi = roi

    while current_roi:
        hierarchy_path.insert(
            0,
            {
                "roi_id": current_roi.roi_id,
                "hierarchy_level": current_roi.hierarchy_level,
                "section_id": current_roi.section_id,
            },
        )

        if current_roi.parent_roi_ref:
            current_roi = await ROI.get(current_roi.parent_roi_ref.id)
        else:
            break

    return {
        "roi_id": roi_id,
        "hierarchy_path": hierarchy_path,
        "total_levels": len(hierarchy_path),
    }


@roi_api.patch("/rois/{roi_id}", response_model=ROI)
async def update_roi(roi_id: str, updated_fields: ROIUpdate = Body(...)):
    """Update details (attributes from ROIBase) of a specific ROI."""
    roi = await ROI.find_one(ROI.roi_id == roi_id)
    if not roi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ROI with ID '{roi_id}' not found",
        )

    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided")

    needs_save = False
    for field, value in update_data.items():
        if hasattr(roi, field) and getattr(roi, field) != value:
            setattr(roi, field, value)
            needs_save = True

    if needs_save:
        roi.updated_at = datetime.now(timezone.utc)
        await roi.save()

    updated_roi = await ROI.get(roi.id, fetch_links=True)
    return updated_roi


@roi_api.delete("/rois/{roi_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_roi(roi_id: str):
    """Delete a specific ROI."""
    roi = await ROI.find_one(ROI.roi_id == roi_id)
    if not roi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ROI with ID '{roi_id}' not found",
        )

    child_rois_count = await ROI.find(ROI.parent_roi_ref.id == roi.id).count()
    if child_rois_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete ROI '{roi_id}' as it has {child_rois_count} child ROIs",
        )

    task_count = await AcquisitionTask.find(AcquisitionTask.roi_ref.id == roi.id).count()
    if task_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete ROI '{roi_id}' as it has {task_count} associated Acquisition Tasks.",
        )

    acq_count = await Acquisition.find(Acquisition.roi_ref.id == roi.id).count()
    if acq_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete ROI '{roi_id}' as it has {acq_count} associated Acquisitions.",
        )

    await roi.delete()
    return None


@roi_api.get("/sections/{section_id}/rois", response_model=list[ROI])
async def list_section_rois(
    section_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve ROIs associated with a specific section using its human-readable ID."""
    rois = (
        await ROI.find({"section_id": section_id}, fetch_links=True).sort("+roi_id").skip(skip).limit(limit).to_list()
    )
    if not rois and not await Section.find_one({"section_id": section_id}):
        raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")

    return rois


@roi_api.get("/rois/{roi_id}/children", response_model=dict)
async def get_child_rois(
    roi_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve child ROIs for a given parent ROI using the parent's hierarchical ID."""
    parent_roi = await ROI.find_one(ROI.roi_id == roi_id)
    if not parent_roi:
        raise HTTPException(status_code=404, detail=f"Parent ROI with ID '{roi_id}' not found")

    children_rois = (
        await ROI.find(ROI.parent_roi_ref.id == parent_roi.id, fetch_links=True)
        .sort("+roi_id")
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    total_child_rois = await ROI.find(ROI.parent_roi_ref.id == parent_roi.id).count()
    more_results = skip + limit < total_child_rois

    return {
        "children": children_rois,
        "metadata": {
            "skip": skip,
            "limit": limit,
            "total_children": total_child_rois,
            "has_more": more_results,
        },
    }
