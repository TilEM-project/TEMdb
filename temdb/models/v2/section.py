from datetime import datetime, timezone
from typing import Any, Dict, Optional

from beanie import Document, Link
from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, IndexModel

from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.enum_schemas import SectionQuality
from temdb.models.v2.substrate import Substrate


class SectioningRunParameters(BaseModel):
    cutting_speed_mms: Optional[float] = Field(
        None, description="Cutting speed in mm/s"
    )
    retract_speed_mms: Optional[float] = Field(
        None, description="Retract speed in mm/s"
    )
    water_level_mm: Optional[float] = Field(
        None, description="Water level in boat in mm"
    )
    wafer_set_level: Optional[float] = Field(None, description="Wafer set level value")
    tape_speed: Optional[float] = Field(None, description="Main tape speed value")
    new_tape_speed: Optional[float] = Field(
        None, description="Temporary tape speed during timePhi"
    )
    tape_cycle: Optional[float] = Field(None, description="Tape cycle duration/value")
    cut_cycle: Optional[float] = Field(None, description="Cut cycle duration/value")
    phiset: Optional[float] = Field(None, description="Phi set value")
    phi_offset: Optional[float] = Field(
        None, description="Actual phi value during picking"
    )
    time_phi: Optional[float] = Field(
        None, description="Time associated with phi movement"
    )
    water_added: Optional[bool] = Field(
        None, description="Flag indicating if water was added during this cycle"
    )
    other_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary for any other arbitrary run parameters",
    )


class SectionMetrics(BaseModel):
    quality: Optional[SectionQuality] = Field(
        None, description="Qualitative state of the section (e.g., Good, Broken)"
    )
    thickness_um: Optional[float] = Field(
        None, description="Measured section thickness in micrometers"
    )
    knife_quality: Optional[str] = Field(
        None, description="Assessment of the knife condition at the time of cutting"
    )
    tissue_confidence_score: Optional[float] = Field(
        None, description="Confidence score for tissue detection on substrate"
    )
    run_parameters: Optional[SectioningRunParameters] = Field(
        None, description="Detailed parameters from the sectioning run"
    )


class SectionBase(BaseModel):
    section_number: int = Field(
        ..., gt=0, description="Sequential section number within the cutting session"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of section creation/cutting",
    )
    optical_image: Optional[Dict] = Field(
        None,
        description="Metadata about optical image collected before imaging (e.g., path, resolution)",
    )
    aperture_uid: Optional[str] = Field(
        None,
        description="UID of the specific aperture holding this section (links to Substrate.apertures.uid)",
    )
    aperture_index: Optional[int] = Field(
        None,
        description="Index of the specific aperture holding this section (links to Substrate.apertures.index)",
    )
    # TODO: Barcode is independent of aperture, do we need this?
    barcode: Optional[str] = Field(
        None, description="Barcode scanned for this section, if any"
    )
    section_metrics: Optional[SectionMetrics] = Field(
        None, description="Metrics and parameters of the section"
    )


class SectionCreate(SectionBase):
    # TODO review this: section_id removed - potentially generated server-side (e.g., using media_id + section_number)
    cutting_session_id: str = Field(
        ..., description="ID of the cutting session this section belongs to"
    )
    media_id: str = Field(
        ...,
        description="ID of the substrate (wafer, tape, etc.) this section is placed on",
    )
    section_number: int = Field(..., gt=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SectionUpdate(BaseModel):
    section_number: Optional[int] = Field(None, gt=0)
    timestamp: Optional[datetime] = None
    optical_image: Optional[Dict] = None
    aperture_uid: Optional[str] = None
    aperture_index: Optional[int] = None
    barcode: Optional[str] = None
    section_metrics: Optional[SectionMetrics] = None


class Section(Document):
    section_id: str = Field(
        ...,
        description="Unique, likely system-generated ID for the section (e.g., MEDIAID_SXXXX)",
    )
    section_number: int = Field(
        ..., gt=0, description="Sequential section number within the cutting session"
    )
    timestamp: datetime = Field(
        ..., description="Timestamp of section creation/cutting"
    )

    cutting_session_id: str = Field(
        ..., description="Human-readable ID of the cutting session"
    )
    block_id: str = Field(..., description="Human-readable ID of the block")
    specimen_id: str = Field(..., description="Human-readable ID of the specimen")
    media_id: str = Field(..., description="Human-readable ID of the substrate")

    cutting_session_ref: Link[CuttingSession] = Field(
        ..., description="Internal Link to the cutting session document"
    )
    substrate_ref: Link[Substrate] = Field(
        ..., description="Internal Link to the substrate document"
    )

    aperture_uid: Optional[str] = Field(
        None, description="UID of the specific aperture holding this section"
    )
    aperture_index: Optional[int] = Field(
        None, description="Index of the specific aperture holding this section"
    )
    barcode: Optional[str] = Field(None, description="Barcode for this section, if any")

    optical_image: Optional[Dict] = Field(
        None, description="Metadata about optical image"
    )
    section_metrics: Optional[SectionMetrics] = Field(
        None, description="Metrics and parameters of the section"
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(None)

    class Settings:
        name = "sections"
        indexes = [
            IndexModel(
                [("section_id", ASCENDING)], unique=True, name="section_id_unique_index"
            ),
            IndexModel(
                [("cutting_session_ref.id", ASCENDING), ("section_number", ASCENDING)],
                name="session_ref_section_number_index",
                unique=True,
            ),
            IndexModel(
                [("substrate_ref.id", ASCENDING), ("section_number", ASCENDING)],
                name="substrate_ref_section_number_index",
            ),
            IndexModel(
                [("substrate_ref.id", ASCENDING), ("aperture_index", ASCENDING)],
                sparse=True,
                name="substrate_aperture_index_index",
            ),
            IndexModel(
                [("substrate_ref.id", ASCENDING), ("aperture_uid", ASCENDING)],
                sparse=True,
                name="substrate_aperture_uid_index",
            ),
            IndexModel(
                [("section_metrics.quality", ASCENDING)],
                sparse=True,
                name="quality_index",
            ),
            IndexModel(
                [("section_metrics.thickness_um", ASCENDING)],
                sparse=True,
                name="thickness_index",
            ),
            IndexModel(
                [("section_metrics.run_parameters.cutting_speed_mms", ASCENDING)],
                sparse=True,
                name="cutting_speed_index",
            ),
            IndexModel([("barcode", ASCENDING)], sparse=True, name="barcode_index"),
            IndexModel([("timestamp", DESCENDING)], name="timestamp_index"),
            IndexModel([("cutting_session_id", ASCENDING)], name="session_hr_id_index"),
            IndexModel([("block_id", ASCENDING)], name="block_hr_id_index"),
            IndexModel([("specimen_id", ASCENDING)], name="specimen_hr_id_index"),
            IndexModel([("media_id", ASCENDING)], name="media_hr_id_index"),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
        ]
