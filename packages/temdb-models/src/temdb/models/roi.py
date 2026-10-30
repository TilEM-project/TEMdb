import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from .base import TEMDBModel, TEMDBRecord


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
    optical_pixel_size: float | None = Field(None, description="Optical resolution in nm per pixel")
    scale_y: float | None = Field(None, description="Scaling factor for y-axis")
    rois: list[Any] | None = Field(None, description="List of ROIs")
    bucket: str | None = Field(None, description="Bucket of ROI")
    corners: dict[str, Any] | None = Field(None, description="Corners of ROI")
    corners_perpendicular: dict[str, Any] | None = Field(None, description="Perpendicular corners of ROI")
    rule: str | None = Field(None, description="Rule for ROI corner detection")
    edits: list[Any] | None = Field(None, description="List of edits to ROI")
    auto_roi: bool | None = Field(None, description="Flag if auto generated ROI was used")
    roi_parameters: dict[str, Any] | None = Field(None, description="Parameters of ROI")
    vertices: list[Any] | None = Field(None, description="Vertices of the ROI polygon")
    rotation_angle: float | None = Field(None, description="Rotation of the ROI polygon in radians")
    buffer_size: float | None = Field(None, description="Dilation of the ROI polygon when imaging, in nanometers")


class ROICreatePayload(ROIPayload):
    vertices: list[tuple[float, float]] = Field(
        ..., min_length=3, description="Vertices of the ROI polygon as [x, y] in nm, relative to the aperture centroid"
    )
    rotation_angle: float = Field(0.0, description="Rotation of the ROI polygon in radians")
    buffer_size: float = Field(0.0, description="Dilation of the ROI polygon when imaging, in nanometers")


class ROIUpdatePayload(ROIPayload):
    vertices: list[tuple[float, float]] = Field(
        None, min_length=3, description="Vertices of the ROI polygon as [x, y] in nm, relative to the aperture centroid"
    )
    rotation_angle: float = Field(None, description="Rotation of the ROI polygon in radians")
    buffer_size: float = Field(None, description="Dilation of the ROI polygon when imaging, in nanometers")


class ROICreate(TEMDBRecord):
    section_id: str = Field(..., description="The section the ROI is drawn on; it gives the substrate and aperture")
    created_at: datetime = Field(
        ..., description="When the ROI was created; with the section's aperture it identifies the ROI on a resend"
    )
    parent_created_at: datetime | None = Field(
        None, description="created_at of the parent ROI on the same section, for a sub-ROI"
    )
    payload: ROICreatePayload = Field(..., description="The ROI's vertices and other domain attributes")


class ROIUpdate(TEMDBRecord):
    payload: ROIUpdatePayload = Field(
        default_factory=ROIUpdatePayload, description="Domain attributes to merge into the ROI"
    )


class ROIResponse(TEMDBRecord):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    roi_id: str = Field(
        ...,
        description="{media_id}.A{aperture:04d}.R{roi_number:03d}, or {media_id}.R{roi_number:04d} on a section "
        "with no aperture; set by TEMdb",
    )
    roi_number: int = Field(
        ...,
        description="Number TEMdb assigned on the aperture (or on the substrate, with no aperture), in create order",
    )
    substrate_media_id: str = Field(..., description="Media ID of the substrate")
    aperture_index: int | None = Field(
        None, description="Index of the layout aperture; none for a section off apertures"
    )
    section_id: str = Field(..., description="The section the ROI is drawn on")
    parent_roi_id: str | None = Field(None, description="ID of the parent ROI")
    dataset_id: uuid.UUID | None = Field(None, description="ID of the dataset this ROI belongs to")
    is_parent: bool = Field(default=False, description="Whether this ROI has child ROIs")

    created_at: datetime = Field(..., description="When the ROI was created")
    updated_at: datetime | None = None

    roi_payload: ROIPayload | None = Field(None, description="Domain attributes of the ROI")


class ROIChildrenMetadata(TEMDBModel):
    skip: int
    limit: int
    total_children: int
    has_more: bool


class ROIChildrenResponse(TEMDBModel):
    """Response model for ROI children query."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    children: list[ROIResponse]
    metadata: ROIChildrenMetadata
