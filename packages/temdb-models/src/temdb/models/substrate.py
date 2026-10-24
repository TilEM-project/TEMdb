from datetime import datetime

from pydantic import ConfigDict, Field

from .base import TEMDBModel, TEMDBRecord
from .enums import ApertureStatus
from .layout import Aperture, SubstrateLayoutResponse


class SubstrateBase(TEMDBRecord):
    """Base substrate fields."""


class SubstrateCreate(SubstrateBase):
    """Schema for creating a substrate."""

    media_id: str = Field(
        ...,
        description="Primary unique identifier for this substrate (e.g., wafer ID, tape reel ID)",
    )
    substrate_layout_id: str = Field(
        ...,
        description="The ID of the substrate layout",
    )
    aperture_status: list[ApertureStatus] | None = Field(
        None,
        description="Status of each aperture in layout order; every aperture starts available if omitted",
    )
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class SubstrateUpdate(SubstrateBase):
    """Schema for updating a substrate."""

    media_id: str = Field(None, description="Primary unique identifier")
    substrate_layout_id: str = Field(
        None, description="Move the substrate to this layout; it must have the same number of apertures"
    )
    aperture_status: dict[int, ApertureStatus] | None = Field(
        None, description="New status for the apertures listed, by aperture index; others are unchanged"
    )


class SubstrateResponse(SubstrateBase):
    """Schema for substrate API responses."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    media_id: str = Field(..., description="Primary unique identifier")
    substrate_layout_id: str = Field(
        ...,
        description="The ID of the substrate layout",
    )
    aperture_status: list[ApertureStatus] = Field(..., description="Status of each aperture in layout order")

    created_at: datetime | None = None
    updated_at: datetime | None = None


class ApertureState(TEMDBModel):
    """One aperture of a substrate: where it is, its status and the sections on it."""

    index: int = Field(..., description="Aperture index in the layout")
    shape: Aperture = Field(..., description="Shape and position of the aperture, from the layout")
    status: ApertureStatus
    sections: list[str] = Field(default_factory=list, description="section_ids of the sections on this aperture")


class SubstrateApertures(TEMDBModel):
    """A substrate's layout with the status and sections of each aperture."""

    media_id: str
    layout: SubstrateLayoutResponse
    apertures: list[ApertureState]
    blank_sections: list[str] = Field(
        default_factory=list, description="section_ids of sections placed on the substrate outside any aperture"
    )
