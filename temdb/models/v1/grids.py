from typing import Dict, List, Optional, Any
from beanie import Document
from pydantic import BaseModel, Field

from pymongo import IndexModel, ASCENDING, DESCENDING


class Metadata(BaseModel):
    grid: str
    grid_int: Optional[int] = None
    specimen_id: Optional[str] = None
    media: Optional[str] = "tape"
    media_id: Optional[str] = None
    session_id: str
    temca_id: str
    roi_creation_time: str
    is_reference: Optional[bool] = False


class GridRecord(BaseModel):
    metadata: Metadata
    data: Optional[List[Dict]] = None
    tile_qc: Optional[Dict] = None
    errors: Optional[List[Any]] = None
    alerts: Optional[List[Any]] = None
    thumbnail: Optional[str] = None
    
class GridUpdate(BaseModel):
    metadata: Optional[Metadata] = None
    data: Optional[Dict] = None
    tile_qc: Optional[Dict] = None
    alerts: Optional[List[str]] = None
    errors: Optional[List[str]] = None
    thumbnail: Optional[str] = None

def specimen_id_to_database_name(specimen_id):
    return specimen_id.replace(".", "_")


class Grid(Document, GridRecord):
    id: str = Field(default_factory=str)

    class Settings:
        name = "grids"
        indices = IndexModel(
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

    @classmethod
    def from_raw_record(cls, record: dict) -> "Grid":
        """Process a raw record and return an instance of Grid"""
        record = cls._create_common_format(record)
        meta = record["metadata"]

        grid = meta["grid"]
        meta["grid_int"] = int(grid)

        session_id = meta["session_id"]
        roi_creation_time = meta["roi_creation_time"]

        if meta["media_id"] is None:
            specimen_id = meta["specimen_id"]
            if (len(session_id) > len(specimen_id)) and session_id.startswith(
                specimen_id
            ):
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
            if (len(session_id) > len(specimen_id)) and session_id.startswith(
                specimen_id
            ):
                temp = session_id.replace(f"{specimen_id}_", "").split("_", 1)[0]
                record["metadata"]["media_id"] = "0" + temp.replace("Tape", "")
            else:
                record["metadata"]["media_id"] = "unknown"

        return record

    async def save_to_db(self):
        """Insert or replace the document in the database."""
        return await self.insert()
