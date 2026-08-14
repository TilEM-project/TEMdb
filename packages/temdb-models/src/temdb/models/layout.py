from datetime import datetime

from pydantic import ConfigDict, Field

from .base import TEMDBModel


class Fiducial(TEMDBModel):
    """Represents a fiducial on a substrate."""

    centroid: tuple[float, float] | None = Field(None, description="Calculated centroid of the fiducial (X, Y)")
    shape: str | None = Field(
        None,
        description="Raw description of the fiducial shape",
    )
    shape_type: str | None = None
    shape_params: dict[str, float] | None = None


class Aperture(TEMDBModel):
    """Represents a single aperture or slot on a substrate."""

    index: int = Field(..., description="Sequential index of the aperture")
    centroid: tuple[float, float] | None = Field(None, description="Calculated centroid of the aperture (X, Y)")
    shape: str | None = Field(
        None,
        description="Raw description of the aperture shape",
    )
    shape_type: str | None = None
    shape_params: dict[str, float] | None = None


class SubstrateLayoutBase(TEMDBModel):
    """Base substrate layout fields."""

    fiducials: list[Fiducial] | None = Field(None, description="List of fiducials on the substrate")
    apertures: list[Aperture] | None = Field(
        None,
        description="List of apertures or slots defined on this substrate",
    )
    media_type: str | None = Field(None, description="Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid')")


class SubstrateLayoutCreate(SubstrateLayoutBase):
    """Schema for creating a substrate layout."""

    layout_id: str = Field(
        ...,
        description="Overall unique identifier for the substrate layout",
    )
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class SubstrateLayoutUpdate(SubstrateLayoutBase):
    """Schema for updating a substrate layout."""


class SubstrateLayoutResponse(SubstrateLayoutBase):
    """Schema for substrate layout API responses."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    layout_id: str = Field(
        ...,
        description="Overall unique identifier for the substrate layout",
    )

    created_at: datetime | None = None
    updated_at: datetime | None = None
