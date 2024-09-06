from fastapi import APIRouter, Body, Query, HTTPException, Depends
from beanie import PydanticObjectId
from typing import List, Optional, Dict

from temdb.dependencies import get_dynamic_model_dependency

from temdb.models.v2.roi import ROI, ROICreate, ROIUpdate
from temdb.models.v2.section import Section
from temdb.models.v2.acquisition import Acquisition


roi_api = APIRouter(
    tags=["ROIs"],
)


@roi_api.get("/rois", response_model=List[ROI])
async def list_rois(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    return await ROI.find_all().skip(skip).limit(limit).to_list()


@roi_api.post("/rois", response_model=ROI)
async def create_roi(roi: ROICreate):
    section = await Section.find_one(
        {"section_number": roi.section_number}, fetch_links=True
    )
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    parent_roi = None
    if roi.parent_roi_id is not None:
        parent_roi = await ROI.find_one({"roi_id": roi.parent_roi_id})
        if not parent_roi:
            raise HTTPException(status_code=404, detail="Parent ROI not found")

    new_roi = ROI(
        roi_id=roi.roi_id,
        aperture_centroid=roi.aperture_centroid,
        aperture_width_height=roi.aperture_width_height,
        aperture_bounding_box=roi.aperture_bounding_box,
        optical_nm_per_pixel=roi.optical_nm_per_pixel,
        scale_y=roi.scale_y,
        barcode=roi.barcode,
        rois=roi.rois,
        bucket=roi.bucket,
        aperture_image=roi.aperture_image,
        roi_mask=roi.roi_mask,
        roi_mask_bucket=roi.roi_mask_bucket,
        corners=roi.corners,
        corners_perpendicular=roi.corners_perpendicular,
        rule=roi.rule,
        edits=roi.edits,
        updated_at=roi.updated_at,
        auto_roi=roi.auto_roi,
        is_lens_correction_roi=roi.is_lens_correction_roi,
        section_number=section.section_number,
        section_id=section.id,
        parent_roi_id=parent_roi,
        roi_parameters=roi.roi_parameters,
    )

    await new_roi.insert()
    return new_roi


@roi_api.get("/rois/{roi_id}", response_model=ROI)
async def get_roi(roi_id: int):
    if roi := await ROI.find_one(ROI.roi_id == roi_id):
        return roi
    else:
        raise HTTPException(status_code=404, detail="ROI not found")


@roi_api.patch("/rois/{roi_id}", response_model=ROI)
async def update_roi(roi_id: int, updated_fields: ROIUpdate = Body(...)):
    existing_roi = await ROI.find_one(ROI.roi_id == roi_id)
    if not existing_roi:
        raise HTTPException(status_code=404, detail="ROI not found")

    update_data = updated_fields.model_dump(exclude_unset=True)

    if update_data:
        for field, value in update_data.items():
            setattr(existing_roi, field, value)

        await existing_roi.save()

    return existing_roi


@roi_api.delete("/rois/{roi_id}", response_model=dict)
async def delete_roi(roi_id: int):
    roi = await ROI.find_one(ROI.roi_id == roi_id)
    if not roi:
        raise HTTPException(status_code=404, detail="ROI not found")

    child_rois = await ROI.find(ROI.parent_roi_id.id == roi_id).to_list()
    if child_rois:
        raise HTTPException(status_code=400, detail="Cannot delete ROI with child ROIs")

    await roi.delete()
    return {"message": "ROI deleted successfully"}


@roi_api.get("/sections/{section_id}/rois", response_model=List[ROI])
async def list_section_rois(
    section_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_lens_correction: Optional[bool] = Query(None),
):
    section = await Section.get(section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    query = {"section.id": section_id}
    if is_lens_correction is not None:
        query["is_lens_correction_roi"] = is_lens_correction

    return await ROI.find(query).skip(skip).limit(limit).to_list()


@roi_api.get("/rois/{roi_id}/children", response_model=Dict)
async def get_child_rois(
    roi_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    parent_roi = await ROI.find_one(ROI.roi_id == roi_id)

    if not parent_roi:
        raise HTTPException(status_code=404, detail="Parent ROI not found")
    children_rois = await ROI.find(ROI.parent_roi_id.id == parent_roi.id).skip(skip).limit(limit).to_list()

    total_child_rois = await ROI.find(ROI.parent_roi_id.id == parent_roi.id).count()
    more_results = skip + limit < total_child_rois
    
    return {
        "children": children_rois,
        "skip": skip,
        "limit": limit,
        "total": total_child_rois,
        "more": more_results
    }
