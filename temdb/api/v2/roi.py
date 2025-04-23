from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, status

from temdb.models.v2.roi import ROI, ROICreate, ROIUpdate
from temdb.models.v2.section import Section
from temdb.models.v2.acquisition import Acquisition
from temdb.models.v2.task import AcquisitionTask

roi_api = APIRouter(
    tags=["ROIs"],
)


@roi_api.get("/rois", response_model=List[ROI])
async def list_rois(
    specimen_id: Optional[str] = Query(
        None, description="Filter by human-readable Specimen ID"
    ),
    block_id: Optional[str] = Query(
        None, description="Filter by human-readable Block ID"
    ),
    cutting_session_id: Optional[str] = Query(
        None, description="Filter by human-readable Cutting Session ID"
    ),
    section_id: Optional[str] = Query(
        None, description="Filter by human-readable Section ID"
    ),
    is_parent_roi: Optional[bool] = Query(
        None, description="Filter ROIs that are parents (have children)"
    ), 
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
        query_filter["cutting_session_id"] = cutting_session_id
    if section_id:
        query_filter["section_id"] = section_id
    if is_parent_roi is not None:
        # TODO: requires checking for children, might need aggregation or separate query
        # Placeholder: query_filter["has_children"] = is_parent_roi # Requires field on model
        pass

    return (
        await ROI.find(query_filter, fetch_links=True).skip(skip).limit(limit).to_list()
    )


@roi_api.post("/rois", response_model=ROI, status_code=status.HTTP_201_CREATED)
async def create_roi(roi_data: ROICreate):
    """Create a new ROI, ensuring roi_id is unique within the parent section."""

    section = await Section.find_one(Section.section_id == roi_data.section_id)
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Section with ID '{roi_data.section_id}' not found")

    existing_roi = await ROI.find_one({
        "roi_id": roi_data.roi_id,
        "section_ref.id": section.id
    })
    if existing_roi:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ROI with ID '{roi_data.roi_id}' already exists in Section '{roi_data.section_id}'"
        )


    parent_roi_ref_id = None
    if roi_data.parent_roi_id is not None:
        parent_roi = await ROI.find_one(ROI.roi_id == roi_data.parent_roi_id)
        if not parent_roi:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Parent ROI with ID '{roi_data.parent_roi_id}' not found")
        parent_roi_ref_id = parent_roi.id

    roi_payload = roi_data.model_dump(exclude={"section_id", "parent_roi_id"})

    new_roi = ROI(
        **roi_payload,
        section_ref=section.id,
        parent_roi_ref=parent_roi_ref_id,
        section_id=section.section_id,
        cutting_session_id=section.cutting_session_id,
        updated_at=datetime.now(timezone.utc)
    )

    await new_roi.insert()
    created_roi = await ROI.get(new_roi.id, fetch_links=True)
    return created_roi


# get_roi remains the same (looks up by globally unique internal ID or non-unique roi_id int)
# NOTE: If GET /rois/{roi_id} should *always* return a single unique ROI,
# then roi_id *must* be globally unique. If it's just an integer label,
# this endpoint might return multiple ROIs or needs context (e.g., /sections/{sid}/rois/{rid})
@roi_api.get("/rois/{roi_id}", response_model=ROI)
async def get_roi(roi_id: int):
    """Retrieve a specific ROI by its human-readable integer ID.
       WARNING: If roi_id is not globally unique, this may return an arbitrary ROI with this ID.
       Consider using a compound path like /sections/{section_id}/rois/{roi_id} for uniqueness.
    """
    roi = await ROI.find_one(ROI.roi_id == roi_id, fetch_links=True)
    if not roi:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"ROI with ID '{roi_id}' not found")
    return roi



@roi_api.patch("/rois/{roi_id}", response_model=ROI)
async def update_roi(roi_id: int, updated_fields: ROIUpdate = Body(...)):
    """Update details (attributes from ROIBase) of a specific ROI."""
    roi = await ROI.find_one(ROI.roi_id == roi_id)
    if not roi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ROI with ID '{roi_id}' not found",
        )

    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No update data provided"
        )

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
async def delete_roi(roi_id: int):
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
        raise HTTPException(status_code=400, detail=f"Cannot delete ROI '{roi_id}' as it has {task_count} associated Acquisition Tasks.")


    acq_count = await Acquisition.find(Acquisition.roi_ref.id == roi.id).count()
    if acq_count > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete ROI '{roi_id}' as it has {acq_count} associated Acquisitions.")

    await roi.delete()
    return None


@roi_api.get("/sections/{section_id}/rois", response_model=List[ROI])
async def list_section_rois(
    section_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve ROIs associated with a specific section using its human-readable ID."""
    rois = (
        await ROI.find({"section_id": section_id}, fetch_links=True)
        .sort("+roi_id")
        .skip(skip)
        .limit(limit)
        .to_list()
    )
    if not rois and not await Section.find_one({"section_id": section_id}):
        raise HTTPException(status_code=404, detail=f"Section '{section_id}' not found")

    return rois


@roi_api.get("/rois/{roi_id}/children", response_model=Dict)
async def get_child_rois(
    roi_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    """Retrieve child ROIs for a given parent ROI using the parent's human-readable ID."""
    parent_roi = await ROI.find_one(ROI.roi_id == roi_id)
    if not parent_roi:
        raise HTTPException(
            status_code=404, detail=f"Parent ROI with ID '{roi_id}' not found"
        )

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
