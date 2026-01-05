from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from temdb.models.enums import SectionQuality


class SectioningRunParameters(BaseModel):
    """Parameters from a sectioning run."""

    model_config = ConfigDict(extra="allow")

    cutting_speed_mms: float | None = Field(None, description="Cutting speed in mm/s")
    retract_speed_mms: float | None = Field(None, description="Retract speed in mm/s")
    water_level_mm: float | None = Field(None, description="Water level in boat in mm")
    wafer_set_level: float | None = Field(None, description="Wafer set level value")
    tape_speed: float | None = Field(None, description="Main tape speed value")
    new_tape_speed: float | None = Field(None, description="Temporary tape speed during timePhi")
    tape_cycle: float | None = Field(None, description="Tape cycle duration/value")
    cut_cycle: float | None = Field(None, description="Cut cycle duration/value")
    phiset: float | None = Field(None, description="Phi set value")
    phi_offset: float | None = Field(None, description="Actual phi value during picking")
    time_phi: float | None = Field(None, description="Time associated with phi movement")
    water_added: bool | None = Field(None, description="Flag indicating if water was added during this cycle")
    other_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary for any other arbitrary run parameters",
    )


class SectionMetrics(BaseModel):
    """Metrics and parameters of a section."""

    model_config = ConfigDict(extra="allow")

    quality: SectionQuality | None = Field(None, description="Qualitative state of the section (e.g., Good, Broken)")
    thickness_um: float | None = Field(None, description="Measured section thickness in micrometers")
    knife_quality: str | None = Field(None, description="Assessment of the knife condition at the time of cutting")
    tissue_confidence_score: float | None = Field(
        None, description="Confidence score for tissue detection on substrate"
    )
    run_parameters: SectioningRunParameters | None = Field(
        None, description="Detailed parameters from the sectioning run"
    )


class SectionBase(BaseModel):
    """Base section fields."""

    model_config = ConfigDict(extra="allow")

    section_number: int | None = Field(None, gt=0, description="Sequential section number within the cutting session")
    timestamp: datetime | None = Field(None, description="Timestamp of section creation/cutting")
    optical_image: dict[str, Any] | None = Field(
        None,
        description="Metadata about optical image collected before imaging",
    )
    aperture_uid: str | None = Field(
        None,
        description="UID of the specific aperture holding this section",
    )
    aperture_index: int | None = Field(
        None,
        description="Index of the specific aperture holding this section",
    )
    barcode: str | None = Field(None, description="Barcode scanned for this section, if any")
    section_metrics: SectionMetrics | None = Field(None, description="Metrics and parameters of the section")


class SectionCreate(SectionBase):
    """Schema for creating a section."""

    cutting_session_id: str = Field(..., description="ID of the cutting session this section belongs to")
    media_id: str = Field(
        ...,
        description="ID of the substrate (wafer, tape, etc.) this section is placed on",
    )
    section_number: int = Field(..., gt=0, description="Sequential section number")


class SectionUpdate(SectionBase):
    """Schema for updating a section."""

    pass


class SectionResponse(SectionBase):
    """Schema for section API responses."""

    section_id: str = Field(..., description="Unique, system-generated ID for the section")
    section_number: int = Field(..., gt=0, description="Sequential section number within the cutting session")
    cutting_session_id: str = Field(..., description="ID of the cutting session")
    block_id: str = Field(..., description="ID of the block")
    specimen_id: str = Field(..., description="ID of the specimen")
    media_id: str = Field(..., description="ID of the substrate")

    created_at: datetime | None = None
    updated_at: datetime | None = None
