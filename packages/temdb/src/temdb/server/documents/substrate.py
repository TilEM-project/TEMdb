from datetime import datetime, timezone

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel
from temdb.models import SubstrateBase


class SubstrateDocument(Document, SubstrateBase):
    """MongoDB document for substrate data."""

    media_id: str = Field(
        ...,
        description="Primary unique identifier for this substrate (e.g., wafer ID, tape reel ID)",
    )
    media_type: str = Field(..., description="Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid')")

    # Override base field with default for document
    status: str | None = Field(
        "new",
        description="Status of the entire substrate (e.g., new, in_use, full, retired, damaged)",
    )

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(None)

    class Settings:
        name = "substrates"
        indexes = [
            IndexModel([("media_id", ASCENDING)], unique=True, name="media_id_unique_index"),
            IndexModel([("media_type", ASCENDING)], name="media_type_index"),
            IndexModel(
                [("uid", ASCENDING)],
                unique=True,
                sparse=True,
                name="substrate_uid_index",
            ),
            IndexModel([("status", ASCENDING)], name="substrate_status_index"),
            IndexModel([("apertures.uid", ASCENDING)], sparse=True, name="aperture_uid_index"),
            IndexModel(
                [("apertures.status", ASCENDING)],
                sparse=True,
                name="aperture_status_index",
            ),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
        ]
