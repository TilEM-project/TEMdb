from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from beanie import Document, Link

from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.v2.enum_schemas import AcquisitionTaskStatus
from temdb.models.v2.specimen import Specimen
from temdb.models.v2.roi import ROI
from temdb.models.v2.block import Block


class AcquisitionTaskCreate(BaseModel):
    task_id: str = Field(..., description="Unique identifier for this task")
    specimen_id: Link[Specimen] = Field(..., description="ID of specimen")
    block_id: Link[Block] = Field(..., description="ID of block")
    roi_id: Link[ROI] = Field(
        ..., description="ID of region of interest to be acquired"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for filtering")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    task_type: str = Field(
        "standard_acquisition", description="Type of acquisition task"
    )
    version: int = Field(1, description="Version number of this task")
    status: AcquisitionTaskStatus = Field(default=AcquisitionTaskStatus.PLANNED)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AcquisitionTaskUpdate(BaseModel):
    status: Optional[AcquisitionTaskStatus] = Field(
        None, description="Status of acquisition task"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    started_at: Optional[datetime] = Field(
        None, description="When task execution began"
    )
    updated_at: Optional[datetime] = Field(
        None, description="When task was last updated"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When task finished (success or failure)"
    )
    tags: List[str] = Field(default_factory=list, description="Tags for filtering")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class AcquisitionTask(Document):
    task_id: str = Field(..., description="Unique identifier for this task")
    task_type: str = Field(
        "standard_acquisition", description="Type of acquisition task"
    )
    version: int = Field(1, description="Version number of this task")

    specimen_id: Link[Specimen] = Field(..., description="ID of specimen")
    block_id: Link[Block] = Field(..., description="ID of block")
    roi_id: Link[ROI] = Field(
        ..., description="ID of region of interest to be acquired"
    )

    status: AcquisitionTaskStatus = Field(default=AcquisitionTaskStatus.PLANNED)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        None, description="When task was last updated"
    )
    started_at: Optional[datetime] = Field(
        None, description="When task execution began"
    )
    completed_at: Optional[datetime] = Field(
        None, description="When task finished (success or failure)"
    )

    error_message: Optional[str] = Field(None, description="Error message if failed")

    tags: List[str] = Field(default_factory=list, description="Tags for filtering")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Settings:
        name = "acquisition_tasks"
        indexes = [
            IndexModel([("task_id", ASCENDING)], unique=False),
            IndexModel([("task_id", ASCENDING), ("version", DESCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("specimen_id.id", ASCENDING), ("block_id.id", ASCENDING)]),
            IndexModel([("roi_id.id", ASCENDING)]),
            IndexModel([("task_type", ASCENDING)]),
            IndexModel([("tags", ASCENDING)]),
        ]

    @classmethod
    async def get_latest_version(cls, task_id: str):
        """Get the latest version of a task"""
        return (
            await cls.find(cls.task_id == task_id)
            .sort([("version", -1)])
            .first_or_none()
        )
