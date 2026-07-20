import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LensCorrectionBase(BaseModel):
    microscope_id: uuid.UUID
    magnification: int
    started_at: datetime
    source_run_id: uuid.UUID | None = None
    source_dataset_id: uuid.UUID | None = None
    shared_transform: dict[str, Any] | None = None
    correction_x_uri: str | None = None
    correction_y_uri: str | None = None
    solver_params: dict[str, Any] | None = None


class LensCorrectionCreate(LensCorrectionBase):
    lc_id: uuid.UUID | None = Field(None, description="Optional client-supplied UUIDv7")
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class LensCorrectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shared_transform: dict[str, Any] | None = None
    correction_x_uri: str | None = None
    correction_y_uri: str | None = None
    solver_params: dict[str, Any] | None = None


class LensCorrectionResponse(LensCorrectionBase):
    lc_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
