from datetime import datetime

from pydantic import ConfigDict, Field

from .base import TEMDBRecord


class MicroscopeBase(TEMDBRecord):
    microscope_type: str = Field("TEM", description="Instrument type")
    model: str | None = Field(None, description="Manufacturer model")
    location: str | None = Field(None, description="Physical location")
    notes: str | None = Field(None, description="Free-form notes")


class MicroscopeCreate(MicroscopeBase):
    microscope_id: str = Field(..., description="Unique readable identifier, e.g. 'T1'")
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class MicroscopeUpdate(TEMDBRecord):
    microscope_type: str | None = None
    model: str | None = None
    location: str | None = None
    notes: str | None = None


class MicroscopeResponse(MicroscopeBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="Internal integer primary key")
    microscope_id: str = Field(..., description="Unique readable identifier, e.g. 'T1'")
    created_at: datetime
    updated_at: datetime | None = None
