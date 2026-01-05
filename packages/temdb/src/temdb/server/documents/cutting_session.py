from datetime import datetime, timezone

from beanie import Document, Link
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel
from temdb.models import CuttingSessionBase

from .block import BlockDocument
from .specimen import SpecimenDocument


class CuttingSessionDocument(Document, CuttingSessionBase):
    """MongoDB document for cutting session data."""

    cutting_session_id: str = Field(..., description="Unique ID of cutting session")
    specimen_id: str = Field(..., description="Human-readable ID of specimen")
    block_id: str = Field(..., description="Human-readable ID of block")

    # Override base fields that are required in the document
    start_time: datetime = Field(..., description="Time when cutting session started")
    sectioning_device: str = Field(..., description="Microtome/Device used for sectioning")
    media_type: str = Field(..., description="Type of substrate the sections are placed upon")

    specimen_ref: Link[SpecimenDocument] = Field(..., description="Internal link to the specimen document")
    block_ref: Link[BlockDocument] = Field(..., description="Internal link to the block document")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(None)

    class Settings:
        name = "cutting_sessions"
        indexes = [
            IndexModel(
                [("cutting_session_id", ASCENDING)],
                unique=True,
                name="session_id_unique_index",
            ),
            IndexModel([("specimen_id", ASCENDING)], name="specimen_hr_id_index"),
            IndexModel([("block_id", ASCENDING)], name="block_hr_id_index"),
            IndexModel(
                [("block_ref.id", ASCENDING), ("start_time", DESCENDING)],
                name="block_ref_start_time_index",
            ),
            IndexModel(
                [("operator", ASCENDING), ("start_time", DESCENDING)],
                sparse=True,
                name="operator_start_time_index",
            ),
            IndexModel([("media_type", ASCENDING)], name="media_type_index"),
            IndexModel([("knife_id", ASCENDING)], sparse=True, name="knife_id_index"),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
        ]
