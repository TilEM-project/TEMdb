from typing import Dict, Optional, Union, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator
from beanie import Document, Link
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
    vertices: Optional[List] = Field(None, description="Vertices of the ROI polygon")

class ROICreate(ROIBase):
    roi_number: int = Field(..., description="Sequential number for this ROI within its parent context")
    section_id: str = Field(..., description="ID of section")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")
    substrate_media_id: str = Field(..., description="Media ID of the substrate this section is placed on")

    section_number: Optional[int] = Field(
        None, description="Number of section from collection"
    )
    parent_roi_id: Optional[str] = Field(
        None, description="Hierarchical ID of parent ROI (e.g., 'SPEC001.BLK001.SEC001.SUB001.ROI001')"
    )

    @field_validator('parent_roi_id', mode='after')
    @classmethod
    def validate_parent_roi_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if '.ROI' not in v:
                raise ValueError('parent_roi_id must contain .ROI and follow format: SPEC###.BLK###.SEC###.SUB###.ROI###[.ROI###...]')
            
            parts = v.split('.')
            if len(parts) < 5:  # SPEC.BLK.SEC.SUB.ROI
                raise ValueError('parent_roi_id must follow format: SPEC###.BLK###.SEC###.SUB###.ROI###[.ROI###...]')
            
            if not parts[-1].startswith('ROI'):
                raise ValueError('parent_roi_id must end with a ROI segment (e.g., ROI001)')
        
        return v

class ROIUpdate(ROIBase):
    updated_at: Optional[datetime] = Field(
        description="Time of last update",
        default_factory=lambda: datetime.now(timezone.utc),
    )

class ROIResponse(ROIBase):
    roi_id: str = Field(..., description="Hierarchical ID of ROI")
    section_id: str = Field(..., description="ID of section")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")
    substrate_media_id: str = Field(..., description="Media ID of the substrate")
    hierarchy_level: int = Field(..., description="Depth level in ROI hierarchy (1=top-level, 2=child, etc.)")
    is_parent: bool = Field(default=False, description="Whether this ROI has child ROIs")

class ROI(Document):
    roi_id: str = Field(
        ..., 
        description="Hierarchical, globally unique ID (e.g., 'SPEC001.BLK001.SEC001.SUB001.ROI001' or 'SPEC001.BLK001.SEC001.SUB001.ROI001.ROI001')"
    )
    roi_number: int = Field(
        ..., 
        description="Sequential number for this ROI within its parent context"
    )
    section_id: str = Field(..., description="Human-readable ID of the parent Section")
    block_id: str = Field(..., description="Human-readable ID of the parent Block")
    specimen_id: str = Field(
        ..., description="Human-readable ID of the parent Specimen"
    )
    substrate_media_id: str = Field(..., description="Media ID of the substrate this section is placed on")
    hierarchy_level: int = Field(
        ..., 
        description="Depth level in ROI hierarchy (1=top-level section ROI, 2=child ROI, etc.)"
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
    vertices: Optional[List] = Field(None, description="Vertices of the ROI polygon")
    updated_at: Optional[datetime] = Field(None, description="Time of last update")

    @classmethod
    def generate_roi_id(cls, specimen_id: str, block_id: str, section_id: str, substrate_media_id: str, roi_number: int, parent_roi_id: Optional[str] = None) -> str:
        """Generate hierarchical ROI ID including substrate."""
        if parent_roi_id:
            return f"{parent_roi_id}.ROI{roi_number:04d}"
        else:
            return f"{specimen_id}.{block_id}.{section_id}.{substrate_media_id}.ROI{roi_number:03d}"

    @classmethod
    def parse_hierarchy_level(cls, roi_id: str) -> int:
        """Calculate hierarchy level from ROI ID."""
        return roi_id.count('.ROI')

    @property
    def is_parent(self) -> bool:
        """TODO Check if this ROI has children (computed property)."""
        return False 

    class Settings:
        name = "rois"
        indexes = [
            IndexModel(
                [("roi_id", ASCENDING)],
                name="roi_id_unique_index",
                unique=True,
            ),
            IndexModel([("section_id", ASCENDING)], name="section_id_index"),
            IndexModel([("block_id", ASCENDING)], name="block_id_index"),
            IndexModel([("specimen_id", ASCENDING)], name="specimen_id_index"),
            IndexModel([("substrate_media_id", ASCENDING)], name="substrate_media_id_index"),
            IndexModel([("hierarchy_level", ASCENDING)], name="hierarchy_level_index"),
            IndexModel([("updated_at", ASCENDING)], name="updated_at_index"),
            IndexModel([("section_ref.id", ASCENDING)], name="section_ref_index"),
            IndexModel(
                [("parent_roi_ref.id", ASCENDING)],
                name="parent_roi_ref_index",
                sparse=True,
            ), 
            IndexModel([("barcode", ASCENDING)], name="barcode_index", sparse=True),
            IndexModel([("section_id", ASCENDING), ("hierarchy_level", ASCENDING)], name="section_hierarchy_index"),
            IndexModel([("specimen_id", ASCENDING), ("block_id", ASCENDING), ("section_id", ASCENDING), ("substrate_media_id", ASCENDING)], name="hierarchy_path_index"),
        ]
