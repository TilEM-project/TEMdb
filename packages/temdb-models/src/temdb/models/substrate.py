from datetime import datetime

from pydantic import ConfigDict, Field

from .base import TEMDBModel
from .enums import ApertureCondition


class SubstrateBase(TEMDBModel):
    """Base substrate fields."""

    condition: dict[int, ApertureCondition] | None = Field(
        None, description="A mapping of aperture indicies to aperture conditions"
    )


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
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class SubstrateUpdate(SubstrateBase):
    """Schema for updating a substrate."""

    media_id: str | None = Field(None, description="Primary unique identifier")


class SubstrateResponse(SubstrateBase):
    """Schema for substrate API responses."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    media_id: str = Field(..., description="Primary unique identifier")
    substrate_layout_id: str = Field(
        ...,
        description="The ID of the substrate layout",
    )

    created_at: datetime | None = None
    updated_at: datetime | None = None
