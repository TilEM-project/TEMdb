from fastapi import APIRouter, Body, Query, HTTPException
from beanie import PydanticObjectId
from typing import List, Optional

from temdb.models.v2.roi import ROI, ROICreate, ROIUpdate
from temdb.models.v2.section import Section
from temdb.models.v2.acquisition import Acquisition

roi_api = APIRouter(
    tags=["ROIs"],
)


@roi_api.get("/rois", response_model=List[ROI])
async def list_rois(skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)):
    return await ROI.find_all().skip(skip).limit(limit).to_list()


@roi_api.get("/rois/{roi_id}/acquisitions", response_model=List[Acquisition])
async def get_roi_acquisitions(
    roi_id: PydanticObjectId,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    roi = await ROI.get(roi_id)
    if not roi:
        raise HTTPException(status_code=404, detail="ROI not found")

    return (
        await Acquisition.find(Acquisition.roi.id == roi_id)
        .skip(skip)
        .limit(limit)
        .to_list()
    )


@roi_api.post("/rois", response_model=ROI)
async def create_roi(roi: ROICreate):
    section = await Section.get(roi.section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    parent_roi = None
    if roi.parent_roi_id:
        parent_roi = await ROI.get(roi.parent_roi_id)
        if not parent_roi:
            raise HTTPException(status_code=404, detail="Parent ROI not found")

    new_roi = ROI(
        roi_id=roi.roi_id,
        name=roi.name,
        aperture_centroid=roi.aperture_centroid,
        brightfield_center=roi.brightfield_center,
        barcode=roi.barcode,
        parameters=roi.parameters,
        is_lens_correction_roi=roi.is_lens_correction_roi,
        section=section,
        parent_roi=parent_roi,
    )
    await new_roi.insert()
    return new_roi


@roi_api.get("/rois/{roi_id}", response_model=ROI)
async def get_roi(roi_id: PydanticObjectId):
    roi = await ROI.get(roi_id)
    if not roi:
        raise HTTPException(status_code=404, detail="ROI not found")
    return roi


@roi_api.patch("/rois/{roi_id}", response_model=ROI)
async def update_roi(roi_id: PydanticObjectId, updated_fields: ROIUpdate = Body(...)):
    existing_roi = await ROI.get(roi_id)
    if not existing_roi:
        raise HTTPException(status_code=404, detail="ROI not found")

    update_data = updated_fields.model_dump(exclude_unset=True)

    if update_data:
        for field, value in update_data.items():
            setattr(existing_roi, field, value)

        await existing_roi.save()

    return existing_roi


@roi_api.delete("/rois/{roi_id}", response_model=dict)
async def delete_roi(roi_id: PydanticObjectId):
    roi = await ROI.get(roi_id)
    if not roi:
        raise HTTPException(status_code=404, detail="ROI not found")

    child_rois = await ROI.find(ROI.parent_roi.id == roi_id).to_list()
    if child_rois:
        raise HTTPException(status_code=400, detail="Cannot delete ROI with child ROIs")

    await roi.delete()
    return {"message": "ROI deleted successfully"}


@roi_api.get("/sections/{section_id}/rois", response_model=List[ROI])
async def list_section_rois(
    section_id: PydanticObjectId,
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


@roi_api.get("/rois/{roi_id}/children", response_model=List[ROI])
async def get_child_rois(
    roi_id: PydanticObjectId,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    parent_roi = await ROI.get(roi_id)
    if not parent_roi:
        raise HTTPException(status_code=404, detail="Parent ROI not found")

    return await ROI.find(ROI.parent_roi.id == roi_id).skip(skip).limit(limit).to_list()


@roi_api.get("/rois/lens-correction", response_model=List[ROI])
async def get_lens_correction_rois(
    skip: int = Query(0, ge=0), limit: int = Query(10, ge=1, le=100)
):
    return (
        await ROI.find(ROI.is_lens_correction_roi is True)
        .skip(skip)
        .limit(limit)
        .to_list()
    )
