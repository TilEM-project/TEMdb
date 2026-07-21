import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from .base import TEMDBModel
from .utils.uri import URI


class ROIPayload(TEMDBModel):
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    aperture_width_height: list[float] | None = Field(
        None,
        description="Width and height of aperture in mm calculated from aperture_image",
    )
    aperture_centroid: list[float] | None = Field(
        None,
        description="Center of aperture measured in pixel coordinates from aperture_image",
    )
    aperture_bounding_box: list[float] | None = Field(
        None,
        description="Bounding box of aperture measured in pixel coordinates",
    )
    aperture_image: URI.Type | None = Field(None, description="URL of aperture image")
    optical_pixel_size: float | None = Field(None, description="Optical resolution in nm per pixel")
    scale_y: float | None = Field(None, description="Scaling factor for y-axis")
    barcode: int | str | None = Field(None, description="Barcode of ROI if present")
    rois: list[Any] | None = Field(None, description="List of ROIs")
    bucket: str | None = Field(None, description="Bucket of ROI")
    roi_mask: URI.Type | None = Field(None, description="URL of ROI mask")
    roi_mask_bucket: str | None = Field(None, description="Bucket of ROI mask")
    corners: dict[str, Any] | None = Field(None, description="Corners of ROI")
    corners_perpendicular: dict[str, Any] | None = Field(None, description="Perpendicular corners of ROI")
    rule: str | None = Field(None, description="Rule for ROI corner detection")
    edits: list[Any] | None = Field(None, description="List of edits to ROI")
    auto_roi: bool | None = Field(None, description="Flag if auto generated ROI was used")
    roi_parameters: dict[str, Any] | None = Field(None, description="Parameters of ROI")
    vertices: list[Any] | None = Field(None, description="Vertices of the ROI polygon")


class ROICreate(TEMDBModel):
    roi_number: int = Field(..., description="Sequential number for this ROI within its parent context")
    section_id: str = Field(..., description="ID of section")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")
    substrate_media_id: str = Field(..., description="Media ID of the substrate this section is placed on")
    section_number: int | None = Field(None, description="Number of section from collection")
    parent_roi_id: str | None = Field(
        None,
        description="Hierarchical ID of parent ROI (e.g., 'SPEC001.BLK001.SEC001.SUB001.ROI001')",
    )
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")
    payload: ROIPayload = Field(default_factory=ROIPayload, description="Domain attributes of the ROI")

    @field_validator("parent_roi_id", mode="after")
    @classmethod
    def validate_parent_roi_id(cls, v: str | None) -> str | None:
        if v is not None:
            if ".ROI" not in v:
                raise ValueError(
                    "parent_roi_id must contain .ROI and follow format: SPEC###.BLK###.SEC###.SUB###.ROI###[.ROI###...]"
                )
            parts = v.split(".")
            if len(parts) < 5:
                raise ValueError("parent_roi_id must follow format: SPEC###.BLK###.SEC###.SUB###.ROI###[.ROI###...]")
            if not parts[-1].startswith("ROI"):
                raise ValueError("parent_roi_id must end with a ROI segment (e.g., ROI001)")
        return v


class ROIUpdate(TEMDBModel):
    payload: ROIPayload = Field(default_factory=ROIPayload, description="Domain attributes to merge into the ROI")


class ROIResponse(TEMDBModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    roi_id: str = Field(..., description="Hierarchical ID of ROI")
    roi_number: int = Field(..., description="Sequential number for this ROI within its parent context")
    section_id: str = Field(..., description="ID of section")
    block_id: str = Field(..., description="ID of block")
    specimen_id: str = Field(..., description="ID of specimen")
    substrate_media_id: str = Field(..., description="Media ID of the substrate")
    hierarchy_level: int = Field(..., description="Depth level in ROI hierarchy (1=top-level, 2=child, etc.)")
    section_number: int | None = Field(None, description="Number of section from collection")
    parent_roi_id: str | None = Field(None, description="Hierarchical ID of parent ROI")
    dataset_id: uuid.UUID | None = Field(None, description="ID of the dataset this ROI belongs to")
    is_parent: bool = Field(default=False, description="Whether this ROI has child ROIs")

    created_at: datetime | None = None
    updated_at: datetime | None = None

    roi_payload: ROIPayload | None = Field(None, description="Domain attributes of the ROI")


class ROIChildrenResponse(TEMDBModel):
    """Response model for ROI children query."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    children: list[ROIResponse]
