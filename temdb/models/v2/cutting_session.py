from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from beanie import Document, Link
from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.v2.block import Block
from temdb.models.v2.specimen import Specimen
from temdb.models.v2.enum_schemas import MediaType


class CuttingSessionCreate(BaseModel):
    cutting_session_id: str = Field(..., description="ID of cutting session")
    start_time: datetime = Field(..., description="Time when cutting session started")
    end_time: Optional[datetime] = Field(None, description="Time when cutting session ended")
    operator: Optional[str] = Field(None, description="Operator of cutting session")
    sectioning_device: str = Field(..., description="Device used for sectioning")
    media_type: MediaType = Field(..., description="Type of substrate the sections are placed upon")
    block_id: str = Field(..., description="ID of block cutting session is associated with")


class CuttingSessionUpdate(BaseModel):
    start_time: Optional[datetime] = Field(None, description="Time when cutting session started")
    end_time: Optional[datetime] = Field(None, description="Time when cutting session ended")
    operator: Optional[str] = Field(None, description="Operator of cutting session")
    sectioning_device: Optional[str] = Field(None, description="Device used for sectioning")
    media_type: Optional[MediaType] = Field(None, description="Type of substrate the sections are placed upon")


class CuttingSession(Document):
    cutting_session_id: str = Field(..., description="ID of cutting session")
    start_time: datetime = Field(..., description="Time when cutting session started")
    end_time: Optional[datetime] = Field(None, description="Time when cutting session ended")
    operator: str = Field(..., description="Operator of cutting session")
    sectioning_device: str = Field(..., description="Device used for sectioning")
    media_type: MediaType = Field(..., description="Type of substrate the sections are placed upon")
    specimen_id: Link[Specimen] = Field(None, description="ID of specimen the cutting session is associated with")
    block_id: Link[Block] = Field(None, description="ID of block the cutting session is associated with")

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
