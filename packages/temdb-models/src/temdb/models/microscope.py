import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MicroscopeBase(BaseModel):
    microscope_type: str = Field("TEM", description="Instrument type")
    model: str | None = Field(None, description="Manufacturer model")
    location: str | None = Field(None, description="Physical location")
    notes: str | None = Field(None, description="Free-form notes")


class MicroscopeCreate(MicroscopeBase):
    label: str = Field(..., description="Unique human handle, e.g. 'TEM-01'")
    microscope_id: uuid.UUID | None = Field(None, description="Optional client-supplied UUIDv7")


class MicroscopeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    microscope_type: str | None = None
    model: str | None = None
    location: str | None = None
    notes: str | None = None


class MicroscopeResponse(MicroscopeBase):
    microscope_id: uuid.UUID
    label: str = Field(..., description="Unique human handle, e.g. 'TEM-01'")
    created_at: datetime
    updated_at: datetime
