from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from beanie import Document, Link
from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.v2.block import Block
from temdb.models.v2.specimen import Specimen


class CuttingSessionCreate(BaseModel):
    cutting_session_id: str = Field(..., description="ID of cutting session")
    start_time: datetime = Field(..., description="Time when cutting session started")
    end_time: Optional[datetime] = Field(
        None, description="Time when cutting session ended"
    )
    operator: Optional[str] = Field(None, description="Operator of cutting session")
    sectioning_device: str = Field(..., description="Device used for sectioning")
    media_type: str = Field(
        ..., description="Type of substrate the sections are placed upon"
    )
    block_id: str = Field(
        ..., description="ID of block cutting session is associated with"
    )
    knife_id: Optional[str] = Field(None, description="Identifier for the knife used")


class CuttingSessionUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    operator: Optional[str] = None
    sectioning_device: Optional[str] = None
    media_type: Optional[str] = None
    knife_id: Optional[str] = None
    block_id: Optional[str] = None
    specimen_id: Optional[str] = None


class CuttingSession(Document):
    cutting_session_id: str = Field(
        ..., description="Unique, likely system-generated ID of cutting session"
    )
    specimen_id: str = Field(
        ..., description="Human-readable ID of specimen (derived from Block)"
    )
    block_id: str = Field(..., description="Human-readable ID of block")

    start_time: datetime = Field(..., description="Time when cutting session started")
    end_time: Optional[datetime] = Field(
        None, description="Time when cutting session ended"
    )
    operator: Optional[str] = Field(
        None, description="Operator of cutting session"
    ) 
    sectioning_device: str = Field(
        ..., description="Microtome/Device used for sectioning"
    )
    media_type: str = Field(
        ..., description="Type of substrate the sections are placed upon"
    )
    knife_id: Optional[str] = Field(None, description="Identifier for the knife used")

    specimen_ref: Link[Specimen] = Field(
        ..., description="Internal link to the specimen document"
    )
    block_ref: Link[Block] = Field(
        ..., description="Internal link to the block document"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(None)

    class Settings:
        name = "cutting_sessions"
        indexes = [
            IndexModel(
                [("cutting_session_id", ASCENDING)],
                unique=True,
                name="session_id_unique_index",
            ),
            IndexModel(
                [("specimen_id", ASCENDING)], name="specimen_hr_id_index"
            ), 
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
            IndexModel(
                [("knife_id", ASCENDING)], sparse=True, name="knife_id_index"
            ),  
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
        ]
