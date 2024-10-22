from typing import Dict, Optional, Union, List
from pydantic import BaseModel
from beanie import Document, Link
from pymongo import IndexModel, ASCENDING

from temdb.models.v2.section import Section


class ROICreate(BaseModel):
    roi_id: int
    specimen_id: str             
    block_id: str                 
    aperture_width_height: Optional[List] = None
    aperture_centroid: Optional[List] = None
    aperture_bounding_box: Optional[List] = None
    optical_nm_per_pixel: Optional[float] = None
    scale_y: Optional[float] = None
    barcode: Optional[Union[int, str]] = None
    rois: Optional[List] = None
    bucket: Optional[str] = None
    aperture_image: Optional[str] = None
    roi_mask: Optional[str] = None
    roi_mask_bucket: Optional[str] = None
    corners: Optional[Dict] = None
    corners_perpendicular: Optional[Dict] = None
    rule: Optional[str] = None
    edits: Optional[List] = None
    updated_at: Optional[str] = None
    auto_roi: Optional[bool] = None
    section_number: int
    parent_roi_id: Optional[int] = None
    roi_parameters: Optional[Dict] = None


class ROIUpdate(BaseModel):
    aperture_width_height: Optional[List] = None
    aperture_centroid: Optional[List] = None
    aperture_bounding_box: Optional[List] = None
    optical_nm_per_pixel: Optional[float] = None
    scale_y: Optional[float] = None
    barcode: Optional[Union[int, str]] = None
    rois: Optional[List] = None
    bucket: Optional[str] = None
    aperture_image: Optional[str] = None
    roi_mask: Optional[str] = None
    roi_mask_bucket: Optional[str] = None
    corners: Optional[Dict] = None
    corners_perpendicular: Optional[Dict] = None
    rule: Optional[str] = None
    edits: Optional[List] = None
    updated_at: Optional[str] = None
    auto_roi: Optional[bool] = None
    parent_roi_id: Optional[str] = None
    roi_parameters: Optional[Dict] = None


class ROI(ROICreate, Document):
    parent_roi_id: Optional[Link["ROI"]]

    class Settings:
        name = "rois"
        indexes = [
            IndexModel(
                [
                    ("specimen_id", ASCENDING),
                    ("block_id", ASCENDING),
                    ("section_number", ASCENDING),
                    ("roi_id", ASCENDING)
                ],
                unique=True,
                name="roi_index"
            ),
            IndexModel(
                [("section_number.id", ASCENDING), ("name", ASCENDING)],
                name="section_name_index",
            ),
            IndexModel([("parent_roi.id", ASCENDING)], name="parent_roi_index"),
            IndexModel(
                [("is_lens_correction_roi", ASCENDING)], name="lens_correction_index"
            ),
        ]

    @classmethod
    async def create_roi(cls, **kwargs):
        # Ensure ROIs are correctly linked to multiple sections
        section_id = kwargs.get("section_id", [])
        for section in section_id:
            if not await Section.exists(section.id):
                raise ValueError(f"Section with id {section.id} does not exist.")
        return await cls(**kwargs).insert()
