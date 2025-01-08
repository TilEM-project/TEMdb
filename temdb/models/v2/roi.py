from typing import Dict, Optional, Union, List
from datetime import datetime
from pydantic import BaseModel, Field
from beanie import Document, Link
from pymongo import IndexModel, ASCENDING

from temdb.models.v2.section import Section


class ROIBase(BaseModel):
    aperture_width_height_mm: Optional[List] = Field(
        None,
        description="Width and height of aperture in mm calculated from aperture_image",
    )
    aperture_centroid: Optional[List] = Field(
        None,
        description="Center of aperture measured in pixel coordinates from aperture_image from top left corner",
    )
    aperture_bounding_box: Optional[List] = Field(
        None,
        description="Bounding box of aperture measured in pixel coordinates from aperture_image from top left corner",
    )
    aperture_image: Optional[str] = Field(None, description="URL of aperture image")
    optical_nm_per_pixel: Optional[float] = Field(
        None, description="Optical resolution in nm per pixel"
    )
    scale_y: Optional[float] = Field(None, description="Scaling factor for y-axis")
    barcode: Optional[Union[int, str]] = Field(
        None, description="Barcode of ROI if present"
    )
    rois: Optional[List] = Field(None, description="List of ROIs")
    bucket: Optional[str] = Field(None, description="Bucket of ROI")
    roi_mask: Optional[str] = Field(None, description="URL of ROI mask")
    roi_mask_bucket: Optional[str] = Field(None, description="Bucket of ROI mask")
    corners: Optional[Dict] = Field(None, description="Corners of ROI")
    corners_perpendicular: Optional[Dict] = Field(..., description="Perpendicular corners of ROI")
    rule: Optional[str] = Field(None, description="Rule for ROI corner detection")
    edits: Optional[List] = Field(None, description="List of edits to ROI")
    updated_at: Optional[datetime] = Field(None, description="Time of last update")
    auto_roi: Optional[bool] = Field(None, description="Flag if auto generated ROI was used")
    roi_parameters: Optional[Dict] = Field(None, description="Parameters of ROI")


class ROICreate(ROIBase):
    roi_id: int = Field(..., description="ID of region of interest")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")
    section_number: int = Field(..., description="Number of section from collection")
    parent_roi_id: Optional[int] = Field(..., description="ID of parent region of interest")


class ROIUpdate(ROIBase):
    section_number: Optional[int] = Field(None, description="Number of section from collection")
    parent_roi_id: Optional[str] = Field(None, description="ID of parent region of interest")


class ROI(ROICreate, Document):
    parent_roi_id: Optional[Link["ROI"]] = Field(None, description="ID of parent region of interest")

    class Settings:
        name = "rois"
        indexes = [
            IndexModel(
                [
                    ("specimen_id", ASCENDING),
                    ("block_id", ASCENDING),
                    ("section_number", ASCENDING),
                    ("roi_id", ASCENDING),
                ],
                unique=True,
                name="roi_index",
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
