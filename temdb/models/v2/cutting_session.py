from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from beanie import Document, Link
from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.v2.block import Block
from temdb.models.v2.specimen import Specimen
from temdb.models.v2.enum_schemas import MediaType


class CuttingSessionCreate(BaseModel):
    cutting_session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    operator: str
    sectioning_device: str
    media_type: MediaType
    block_id: str


class CuttingSessionUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    operator: Optional[str] = None
    sectioning_device: Optional[str] = None
    media_type: Optional[MediaType] = None


class CuttingSession(Document):
    cutting_session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    operator: str
    sectioning_device: str
    media_type: MediaType
    specimen_id: Link[Specimen]
    block_id: Link[Block]

    class Settings:
        name = "cutting_sessions"
        indexes = [
            IndexModel(
                [("cutting_session_id", ASCENDING)], unique=True, name="session_id_index"
            ),
            IndexModel(
                [("block_id.id", ASCENDING), ("start_time", DESCENDING)],
                name="block_start_time_index",
            ),
            IndexModel(
                [("operator", ASCENDING), ("start_time", DESCENDING)],
                name="operator_start_time_index",
            ),
            IndexModel([("media_type", ASCENDING)], name="media_type_index"),
        ]
