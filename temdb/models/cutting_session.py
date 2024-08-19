from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from beanie import PydanticObjectId, Document, Link
from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.block import Block
from temdb.models.enum_schemas import MediaType


class CuttingSessionCreate(BaseModel):
    session_id: str
    start_time: datetime
    end_time: datetime
    operator: str
    sectioning_device: str
    media_type: MediaType
    block_id: PydanticObjectId


class CuttingSessionUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    operator: Optional[str] = None
    sectioning_device: Optional[str] = None
    media_type: Optional[MediaType] = None


class CuttingSession(Document):
    session_id: str
    start_time: datetime
    end_time: datetime
    operator: str
    sectioning_device: str
    media_type: MediaType
    block: Link[Block]

    class Settings:
        name = "cutting_sessions"
        indexes = [
            IndexModel(
                [("session_id", ASCENDING)], unique=True, name="session_id_index"
            ),
            IndexModel(
                [("block.id", ASCENDING), ("start_time", DESCENDING)],
                name="block_start_time_index",
            ),
            IndexModel(
                [("operator", ASCENDING), ("start_time", DESCENDING)],
                name="operator_start_time_index",
            ),
            IndexModel([("media_type", ASCENDING)], name="media_type_index"),
        ]
