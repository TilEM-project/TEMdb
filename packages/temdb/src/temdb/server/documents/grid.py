import logging
from typing import Any

from beanie import Document
from pydantic import BaseModel, Field
from pymongo import ASCENDING, IndexModel

logger = logging.getLogger(__name__)


class GridMetadata(BaseModel):
    """Metadata for a grid acquisition."""

    grid: str
    grid_int: int | None = None
    specimen_id: str | None = None
    media: str | None = "tape"
    media_id: str | None = None
    session_id: str
    temca_id: str
    roi_creation_time: str
    is_reference: bool | None = False


class GridRecord(BaseModel):
    """Record structure for grid data."""

    metadata: GridMetadata
    data: list[dict[str, Any]] | None = None
    tile_qc: dict[str, Any] | None = None
    errors: list[Any] | None = None
    alerts: list[Any] | None = None
    thumbnail: str | None = None


class GridUpdate(BaseModel):
    """Schema for updating a grid."""

    metadata: GridMetadata | None = None
    data: dict[str, Any] | None = None
    tile_qc: dict[str, Any] | None = None
    alerts: list[str] | None = None
    errors: list[str] | None = None
    thumbnail: str | None = None


class GridDocument(Document, GridRecord):
    """Grid document for MongoDB storage."""

    id: str = Field(..., alias="_id")

    class Settings:
        name = "grids"
        indexes = [
            IndexModel(
                [
                    ("metadata.grid_int", ASCENDING),
                    ("metadata.session_id", ASCENDING),
                    ("metadata.media_id", ASCENDING),
                    ("metadata.temca_id", ASCENDING),
                    ("metadata.is_reference", ASCENDING),
                    ("metadata.roi_creation_time", ASCENDING),
                    ("errors", ASCENDING),
                ]
            )
        ]

    @classmethod
    def from_raw_record(cls, record: dict) -> "GridDocument":
        """Process a raw record and return an instance of GridDocument."""
        record = cls._create_common_format(record)
        meta = record["metadata"]

        grid = meta["grid"]
        meta["grid_int"] = int(grid)

        session_id = meta["session_id"]
        roi_creation_time = meta["roi_creation_time"]

        if meta["media_id"] is None:
            specimen_id = meta["specimen_id"]
            if (len(session_id) > len(specimen_id)) and session_id.startswith(specimen_id):
                temp = session_id.replace(f"{specimen_id}_", "").split("_", 1)[0]
                meta["media_id"] = "0" + temp.replace("Tape", "")
            else:
                meta["media_id"] = "unknown"

        record_id = f"{session_id}_{grid}_{roi_creation_time}"
        record["_id"] = record_id

        return cls(**record)

    @staticmethod
    def _create_common_format(record: dict) -> dict:
        """Converts a raw record to a common format for MongoDB storage."""
        if isinstance(record, list):
            new_record = {
                "metadata": record[0].get("metadata"),
                "data": record[1].get("data"),
            }
            if len(record) > 2:
                for k, v in record[2].items():
                    new_record[k] = v
            record = new_record
        elif not isinstance(record, dict):
            raise ValueError("Unknown record format (should be dict or list).")

        record["tile_qc"] = record.get("tile_qc") or {}
        record["alerts"] = record.get("alerts") or []
        record["errors"] = record.get("errors") or []
        record["thumbnail"] = record.get("thumbnail") or ""

        grid = record["metadata"]["grid"]
        if "_reference" in grid:
            record["metadata"]["grid"] = grid.replace("_reference", "")

        record["metadata"]["grid_int"] = int(record["metadata"]["grid"])
        if record["metadata"]["specimen_id"] is None:
            record["metadata"]["specimen_id"] = "17797_1R"
        if record["metadata"]["media"] is None:
            record["metadata"]["media"] = "tape"

        if record["metadata"].get("media_id") is None:
            session_id = record["metadata"]["session_id"]
            specimen_id = record["metadata"]["specimen_id"]
            if (len(session_id) > len(specimen_id)) and session_id.startswith(specimen_id):
                temp = session_id.replace(f"{specimen_id}_", "").split("_", 1)[0]
                record["metadata"]["media_id"] = "0" + temp.replace("Tape", "")
            else:
                record["metadata"]["media_id"] = "unknown"

        return record

    async def save_to_db(self):
        """Insert or replace the document in the database."""
        return await self.insert()
