from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReferencePoints(BaseModel):
    """Reference points for substrate calibration."""

    model_config = ConfigDict(extra="allow")

    origin: tuple[float, float, float] | None = Field(None, description="Origin point (x, y, z)")
    end: tuple[float, float, float] | None = Field(None, description="End point (x, y, z)")
    ref: tuple[float, float, float] | None = Field(None, description="Reference point (x, y, z)")


class Aperture(BaseModel):
    """Represents a single aperture or slot on a substrate."""

    model_config = ConfigDict(extra="allow")

    uid: str = Field(
        ...,
        description="Unique identifier for this aperture within the substrate",
    )
    index: int = Field(..., description="Sequential index of the aperture")
    centroid: tuple[float, float, float] | None = Field(
        None, description="Calculated centroid of the aperture (X, Y, Z)"
    )
    shape: str | None = Field(
        None,
        description="Raw description of the aperture shape",
    )
    shape_type: str | None = None
    shape_params: dict[str, Any] | None = None
    status: str | None = Field(None, description="Status of the aperture (e.g., available, used, damaged)")
    tracking_uid: str | None = Field(
        None,
        alias="tuid",
        description="Tracking UID from source if available",
    )


class SubstrateMetadata(BaseModel):
    """General metadata about a substrate."""

    model_config = ConfigDict(extra="allow")

    name: str | None = Field(None, description="User-defined name for the substrate")
    user: str | None = Field(None, description="User associated with substrate creation/calibration")
    created: datetime | None = Field(None, description="Timestamp from source metadata 'created'")
    calibrated: datetime | None = Field(None, description="Timestamp from source metadata 'calibrated'")
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary for any other key-value metadata items",
    )


class SubstrateBase(BaseModel):
    """Base substrate fields."""

    model_config = ConfigDict(extra="allow")

    uid: str | None = Field(
        None,
        description="Overall unique identifier for the substrate instance",
    )
    status: str | None = Field(
        None,
        description="Status of the entire substrate (e.g., new, in_use, full, retired)",
    )
    refpoint: ReferencePoints | None = Field(None, description="Reference points in local substrate coordinates")
    refpoint_world: ReferencePoints | None = Field(
        None, description="Reference points mapped to world/stage coordinates"
    )
    source_path: str | None = Field(
        None,
        description="Path or identifier of the source file defining this substrate",
    )
    metadata: SubstrateMetadata | None = Field(None, description="General metadata about the substrate")
    apertures: list[Aperture] | None = Field(
        None,
        description="List of apertures or slots defined on this substrate",
    )


class SubstrateCreate(SubstrateBase):
    """Schema for creating a substrate."""

    media_id: str = Field(
        ...,
        description="Primary unique identifier for this substrate (e.g., wafer ID, tape reel ID)",
    )
    media_type: str = Field(..., description="Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid')")
    status: str | None = Field(
        "new",
        description="Status of the entire substrate",
    )


class SubstrateUpdate(SubstrateBase):
    """Schema for updating a substrate."""

    media_id: str | None = Field(None, description="Primary unique identifier")
    media_type: str | None = Field(None, description="Type of substrate")


class SubstrateResponse(SubstrateBase):
    """Schema for substrate API responses."""

    media_id: str = Field(..., description="Primary unique identifier")
    media_type: str = Field(..., description="Type of substrate")

    created_at: datetime | None = None
    updated_at: datetime | None = None
