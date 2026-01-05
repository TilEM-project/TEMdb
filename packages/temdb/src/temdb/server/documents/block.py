from datetime import datetime, timezone

from beanie import Document, Link
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel
from temdb.models import BlockBase

from .specimen import SpecimenDocument


class BlockDocument(Document, BlockBase):
    """MongoDB document for block data."""

    block_id: str = Field(..., description="ID of the block within the specimen")
    specimen_id: str = Field(..., description="ID of specimen this block belongs to")
    specimen_ref: Link[SpecimenDocument] = Field(..., description="Internal link to the specimen document")
    description: str | None = Field(None, description="Description of the block")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time when block metadata was created",
    )
    updated_at: datetime | None = Field(None, description="Time when block metadata was last updated")

    class Settings:
        name = "blocks"
        indexes = [
            IndexModel(
                [("specimen_id", ASCENDING), ("block_id", ASCENDING)],
                unique=True,
                name="specimen_block_id_index",
            ),
            IndexModel([("specimen_ref.id", ASCENDING)], name="specimen_ref_index"),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
        ]
