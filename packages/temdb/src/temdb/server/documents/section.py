from datetime import datetime, timezone

from beanie import Document, Link
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel
from temdb.models import SectionBase

from .cutting_session import CuttingSessionDocument
from .substrate import SubstrateDocument


class SectionDocument(Document, SectionBase):
    """MongoDB document for section data."""

    section_id: str = Field(
        ...,
        description="Unique, system-generated ID for the section (e.g., MEDIAID_SXXXX)",
    )

    # Override base field - required in document
    section_number: int = Field(..., gt=0, description="Sequential section number within the cutting session")
    # Override base field - has default factory in document
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of section creation/cutting",
    )

    cutting_session_id: str = Field(..., description="Human-readable ID of the cutting session")
    block_id: str = Field(..., description="Human-readable ID of the block")
    specimen_id: str = Field(..., description="Human-readable ID of the specimen")
    media_id: str = Field(..., description="Human-readable ID of the substrate")

    cutting_session_ref: Link[CuttingSessionDocument] = Field(
        ..., description="Internal Link to the cutting session document"
    )
    substrate_ref: Link[SubstrateDocument] = Field(..., description="Internal Link to the substrate document")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(None)

    class Settings:
        name = "sections"
        indexes = [
            IndexModel([("section_id", ASCENDING)], unique=True, name="section_id_unique_index"),
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
            IndexModel([("barcode", ASCENDING)], sparse=True, name="barcode_index"),
            IndexModel([("timestamp", DESCENDING)], name="timestamp_index"),
            IndexModel([("cutting_session_id", ASCENDING)], name="session_hr_id_index"),
            IndexModel([("block_id", ASCENDING)], name="block_hr_id_index"),
            IndexModel([("specimen_id", ASCENDING)], name="specimen_hr_id_index"),
            IndexModel([("media_id", ASCENDING)], name="media_hr_id_index"),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
        ]
