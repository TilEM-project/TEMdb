from datetime import datetime, timezone

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel
from temdb.models import SpecimenBase


class SpecimenDocument(Document, SpecimenBase):
    """MongoDB document for specimen data."""

    specimen_id: str = Field(..., description="ID of specimen")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time when specimen metadata was created",
    )
    updated_at: datetime | None = Field(None, description="Time when specimen metadata was last updated")

    class Settings:
        name = "specimens"
        indexes = [
            IndexModel([("specimen_id", ASCENDING)], unique=True, name="specimen_id_index"),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
        ]
