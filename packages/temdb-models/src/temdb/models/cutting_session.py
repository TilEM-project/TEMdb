from __future__ import annotations

from datetime import datetime

from pydantic import ConfigDict, Field

from .base import TEMDBModel
from .enums import EventType


class CuttingSessionEvent(TEMDBModel):
    """Event related to a cutting session."""

    label: str = Field(..., description="Label or name of the event")
    timestamp: datetime = Field(..., description="The time when the event occurred")
    event_type: EventType = Field(..., description="Type of the event")
    description: str | None = Field(None, description="Additional details about the event")


class CuttingSessionEvents(TEMDBModel):
    """Collection of events related to a cutting session."""

    automated_knife_cleanings: list[CuttingSessionEvent] | None = Field(
        None, description="List of automated knife cleaning events associated with the cutting session"
    )
    manual_knife_cleanings: list[CuttingSessionEvent] | None = Field(
        None, description="List of manual knife cleaning events associated with the cutting session"
    )
    water_additions: list[CuttingSessionEvent] | None = Field(
        None, description="List of water addition events associated with the cutting session"
    )


class CuttingSessionBase(TEMDBModel):
    """Base cutting session fields."""

    start_time: datetime | None = Field(None, description="Time when cutting session started")
    end_time: datetime | None = Field(None, description="Time when cutting session ended")
    operator: str | None = Field(None, description="Operator of cutting session")
    sectioning_device: str | None = Field(None, description="Microtome/Device used for sectioning")
    media_type: str | None = Field(None, description="Type of substrate the sections are placed upon")
    knife_id: str | None = Field(None, description="Identifier for the knife used")
    cutting_session_events: CuttingSessionEvents | None = Field(
        None, description="Collection of events related to this cutting session"
    )


class CuttingSessionCreate(CuttingSessionBase):
    """Schema for creating a cutting session."""

    cutting_session_id: str = Field(..., description="Unique cutting session identifier")
    block_id: str = Field(..., description="ID of block cutting session is associated with")
    start_time: datetime = Field(..., description="Time when cutting session started")
    sectioning_device: str = Field(..., description="Device used for sectioning")
    media_type: str = Field(..., description="Type of substrate the sections are placed upon")
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class CuttingSessionUpdate(CuttingSessionBase):
    """Schema for updating a cutting session."""

    block_id: str | None = Field(None, description="ID of block")
    specimen_id: str | None = Field(None, description="ID of specimen")


class CuttingSessionResponse(CuttingSessionBase):
    """Schema for cutting session API responses."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    cutting_session_id: str = Field(..., description="Unique cutting session identifier")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")
    start_time: datetime = Field(..., description="Time when cutting session started")
    sectioning_device: str = Field(..., description="Device used for sectioning")
    media_type: str = Field(..., description="Type of substrate the sections are placed upon")

    created_at: datetime | None = None
    updated_at: datetime | None = None
