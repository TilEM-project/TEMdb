from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator, model_validator

from .enums import SECTION_CONDITIONS, SectionQuality
from .utils.uri import URI


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


class SectionMetric(BaseModel):
    """Section Metric with Confidence"""

    model_config = ConfigDict(extra="allow")

    confidence: float | None = Field(None, description="The confidence value of this metric.", ge=0, le=1)
    label: Any | None = Field(None, description="")
    pass_status: bool = Field(True, description="Should be True if the section is of good quality by this metric.")
    message: str | None = Field(None, description="Additional human readable infomation about this metric.")


class SectionMetrics(BaseModel):
    """Metrics and parameters of a section."""

    model_config = ConfigDict(extra="allow")

    quality: SectionQuality | None = Field(None, description="Qualitative state of the section (e.g., Good, Broken)")
    thickness_um: SectionMetric | None = Field(None, description="Measured section thickness in micrometers")
    thickness_consistency: SectionMetric | None = Field(None, description="Measured section thischness consistency")
    knife_marks: SectionMetric | None = Field(
        None, description="Assessment of the knife condition at the time of cutting"
    )
    coverage: SectionMetric | None = Field(None, description="")
    shape: SectionMetric | None = Field(None, description="")
    run_parameters: SectioningRunParameters | None = Field(
        None, description="Detailed parameters from the sectioning run"
    )


class OpticalImage(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    image_path: URI.Type = Field(description="The URI of where the optical image is stored")
    metadata: dict[str, Any] = Field({}, description="Metadata about this optical image")


class SectionBase(BaseModel):
    """Base section fields."""

    model_config = ConfigDict(extra="allow")

    section_number: int | None = Field(None, gt=0, description="Sequential section number within the cutting session")
    timestamp: datetime | None = Field(None, description="Timestamp of section creation/cutting")
    optical_image: dict[str, Any] | None = Field(
        None,
        description="Optical image collected before imaging",
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
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class SectionUpdate(SectionBase):
    """Schema for updating a section."""

    model_config = ConfigDict(extra="forbid")

    condition: str | None = Field(None, description="Physical condition of the section")
    condition_reason: str | None = Field(None, description="Reason for the current condition")

    @model_validator(mode="before")
    @classmethod
    def reject_destroyed(cls, data: Any) -> Any:
        if isinstance(data, dict) and "destroyed" in data:
            raise ValueError("`destroyed` is read-only; set condition='destroyed' instead")
        return data

    @field_validator("condition")
    @classmethod
    def validate_condition(cls, value: str | None) -> str | None:
        if value is not None and value not in SECTION_CONDITIONS:
            raise ValueError(f"condition must be one of {SECTION_CONDITIONS}")
        return value


class SectionResponse(SectionBase):
    """Schema for section API responses."""

    section_id: str = Field(..., description="Unique, system-generated ID for the section")
    section_number: int = Field(..., gt=0, description="Sequential section number within the cutting session")
    cutting_session_id: str = Field(..., description="ID of the cutting session")
    block_id: str = Field(..., description="ID of the block")
    specimen_id: str = Field(..., description="ID of the specimen")
    media_id: str = Field(..., description="ID of the substrate")
    condition: str = Field("ok", description="Physical condition of the section")
    condition_reason: str | None = Field(None, description="Reason for the current condition")

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def drop_wire_destroyed(cls, data: Any) -> Any:
        if isinstance(data, dict) and "destroyed" in data:
            data = {key: value for key, value in data.items() if key != "destroyed"}
        return data

    @computed_field(description="Deprecated: derived from condition == 'destroyed'")
    @property
    def destroyed(self) -> bool:
        return self.condition == "destroyed"
