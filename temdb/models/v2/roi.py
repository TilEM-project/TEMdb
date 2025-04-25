from typing import Dict, Optional, Union, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from beanie import Document, Link, Indexed
from pymongo import IndexModel, ASCENDING

from temdb.models.v2.section import Section


class ROIBase(BaseModel):
    aperture_width_height: Optional[List] = Field(
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
    optical_pixel_size: Optional[float] = Field(
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
    corners_perpendicular: Optional[Dict] = Field(
        None, description="Perpendicular corners of ROI"
    )
    rule: Optional[str] = Field(None, description="Rule for ROI corner detection")
    edits: Optional[List] = Field(None, description="List of edits to ROI")
    auto_roi: Optional[bool] = Field(
        None, description="Flag if auto generated ROI was used"
    )
    roi_parameters: Optional[Dict] = Field(None, description="Parameters of ROI")


class ROICreate(ROIBase):
    roi_id: int = Field(..., description="ID of region of interest")
    section_id: str = Field(..., description="ID of section")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")
    section_number: Optional[int] = Field(
        None, description="Number of section from collection"
    )
    parent_roi_id: Optional[int] = Field(
        None, description="ID of parent region of interest"
    )


class ROIUpdate(ROIBase):
    updated_at: Optional[datetime] = Field(
        description="Time of last update",
        default_factory=lambda: datetime.now(timezone.utc),
    )

class ROIResponse(ROIBase):
    roi_id: int = Field(..., description="ID of region of interest")
    section_id: str = Field(..., description="ID of section")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")

class ROI(Document):
    roi_id: int = Field(
        ..., description="Unique, human-readable integer ID for this ROI"
    )
    section_id: str = Field(..., description="Human-readable ID of the parent Section")
    cutting_session_id: str = Field(
        ..., description="Human-readable ID of the parent Cutting Session"
    )
    block_id: str = Field(..., description="Human-readable ID of the parent Block")
    specimen_id: str = Field(
        ..., description="Human-readable ID of the parent Specimen"
    )

    section_ref: Link[Section] = Field(
        ..., description="Internal link to the section document"
    )
    parent_roi_ref: Optional[Link["ROI"]] = Field(
        None, description="Internal link to the parent ROI document, if any"
    )

    section_number: Optional[int] = Field(None)
    aperture_width_height: Optional[List] = Field(None)
    aperture_centroid: Optional[List] = Field(None)
    aperture_bounding_box: Optional[List] = Field(None)
    aperture_image: Optional[str] = Field(None)
    optical_pixel_size: Optional[float] = Field(None)
    scale_y: Optional[float] = Field(None)
    barcode: Optional[Union[int, str]] = Field(None)
    rois: Optional[List] = Field(None)
    bucket: Optional[str] = Field(None)
    roi_mask: Optional[str] = Field(None)
    roi_mask_bucket: Optional[str] = Field(None)
    corners: Optional[Dict] = Field(None)
    corners_perpendicular: Optional[Dict] = Field(None)
    rule: Optional[str] = Field(None)
    edits: Optional[List] = Field(None)
    auto_roi: Optional[bool] = Field(None)
    roi_parameters: Optional[Dict] = Field(None)
    updated_at: Optional[datetime] = Field(None, description="Time of last update")

    class Settings:
        name = "rois"
        indexes = [
            IndexModel(
                [("section_ref.id", ASCENDING), ("roi_id", ASCENDING)],
                name="section_ref_roi_id_unique_index",
                unique=True,
            ),
            IndexModel([("section_id", ASCENDING)], name="section_id_index"),
            IndexModel([("cutting_session_id", ASCENDING)], name="session_id_index"),
            IndexModel([("block_id", ASCENDING)], name="block_id_index"),
            IndexModel([("specimen_id", ASCENDING)], name="specimen_id_index"),
            IndexModel([("updated_at", ASCENDING)], name="updated_at_index"),
            IndexModel([("section_ref.id", ASCENDING)], name="section_ref_index"),
            IndexModel(
                [("parent_roi_ref.id", ASCENDING)],
                name="parent_roi_ref_index",
                sparse=True,
            ),  # sparse if not all ROIs have parents
            IndexModel([("barcode", ASCENDING)], name="barcode_index", sparse=True),
            IndexModel([("section_id", ASCENDING)], name="section_hr_id_index"),
            IndexModel([("cutting_session_id", ASCENDING)], name="session_hr_id_index"),
            IndexModel([("block_id", ASCENDING)], name="block_hr_id_index"),
            IndexModel([("specimen_id", ASCENDING)], name="specimen_hr_id_index"),
        ]
