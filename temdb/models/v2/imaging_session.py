from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from beanie import Document, Link, PydanticObjectId

from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.v2.enum_schemas import ImagingSessionStatus, MediaType
from temdb.models.v2.specimen import Specimen
from temdb.models.v2.roi import ROI
from temdb.models.v2.block import Block


class ImagingSessionCreate(BaseModel):
    session_id: str
    specimen_id: PydanticObjectId
    block_id: PydanticObjectId
    media_type: MediaType
    media_id: str


class ImagingSessionUpdate(BaseModel):
    status: Optional[ImagingSessionStatus] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class ImagingSession(Document):
    session_id: str
    specimen_id: Link[Specimen]
    block: Link[Block]
    media_type: MediaType
    media_id: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: ImagingSessionStatus = ImagingSessionStatus.PLANNED
    rois: List[ROI] = []

    class Settings:
        name = "imaging_sessions"
        indexes = [
            IndexModel(
                [("session_id", ASCENDING)], unique=True, name="session_id_index"
            ),
            IndexModel(
                [
                    ("specimen.id", ASCENDING),
                    ("block.id", ASCENDING),
                    ("media_id", ASCENDING),
                ],
                name="specimen_block_media_index",
            ),
            IndexModel(
                [("media_type", ASCENDING), ("media_id", ASCENDING)],
                name="media_type_id_index",
            ),
            IndexModel(
                [("status", ASCENDING), ("start_time", DESCENDING)],
                name="status_start_time_index",
            ),
        ]
