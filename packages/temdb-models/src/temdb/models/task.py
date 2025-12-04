from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from temdb.models.enums import AcquisitionTaskStatus


class AcquisitionTaskBase(BaseModel):
    """Base acquisition task fields."""

    model_config = ConfigDict(extra="allow")

    task_type: str | None = Field(None, description="Type of acquisition task")
    version: int | None = Field(None, description="Version number of this task")
    status: AcquisitionTaskStatus | None = Field(None, description="Status of acquisition task")
    error_message: str | None = Field(None, description="Error message if failed")
    started_at: datetime | None = Field(None, description="When task execution began")
    completed_at: datetime | None = Field(None, description="When task finished (success or failure)")
    tags: list[str] | None = Field(None, description="Tags for filtering")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class AcquisitionTaskCreate(AcquisitionTaskBase):
    """Schema for creating an acquisition task."""

    task_id: str = Field(..., description="Unique identifier for this task")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")
    roi_id: str = Field(..., description="ID of region of interest to be acquired")
    task_type: str = Field(default="standard_acquisition", description="Type of acquisition task")
    version: int = Field(default=1, description="Version number of this task")
    status: AcquisitionTaskStatus = Field(default=AcquisitionTaskStatus.PLANNED)
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AcquisitionTaskUpdate(AcquisitionTaskBase):
    """Schema for updating an acquisition task."""

    pass


class AcquisitionTaskResponse(AcquisitionTaskBase):
    """Schema for acquisition task API responses."""

    task_id: str = Field(..., description="Unique identifier for this task")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")
    roi_id: str = Field(..., description="ID of region of interest")
    task_type: str = Field(..., description="Type of acquisition task")
    version: int = Field(..., description="Version number of this task")
    status: AcquisitionTaskStatus = Field(..., description="Status of acquisition task")

    created_at: datetime | None = None
    updated_at: datetime | None = None
