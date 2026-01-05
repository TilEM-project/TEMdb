from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CuttingSessionBase(BaseModel):
    """Base cutting session fields."""

    model_config = ConfigDict(extra="allow")

    start_time: datetime | None = Field(None, description="Time when cutting session started")
    end_time: datetime | None = Field(None, description="Time when cutting session ended")
    operator: str | None = Field(None, description="Operator of cutting session")
    sectioning_device: str | None = Field(None, description="Microtome/Device used for sectioning")
    media_type: str | None = Field(None, description="Type of substrate the sections are placed upon")
    knife_id: str | None = Field(None, description="Identifier for the knife used")


class CuttingSessionCreate(CuttingSessionBase):
    """Schema for creating a cutting session."""

    cutting_session_id: str = Field(..., description="Unique cutting session identifier")
    block_id: str = Field(..., description="ID of block cutting session is associated with")
    start_time: datetime = Field(..., description="Time when cutting session started")
    sectioning_device: str = Field(..., description="Device used for sectioning")
    media_type: str = Field(..., description="Type of substrate the sections are placed upon")


class CuttingSessionUpdate(CuttingSessionBase):
    """Schema for updating a cutting session."""

    block_id: str | None = Field(None, description="ID of block")
    specimen_id: str | None = Field(None, description="ID of specimen")


class CuttingSessionResponse(CuttingSessionBase):
    """Schema for cutting session API responses."""

    cutting_session_id: str = Field(..., description="Unique cutting session identifier")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")
    start_time: datetime = Field(..., description="Time when cutting session started")
    sectioning_device: str = Field(..., description="Device used for sectioning")
    media_type: str = Field(..., description="Type of substrate the sections are placed upon")

    created_at: datetime | None = None
    updated_at: datetime | None = None
