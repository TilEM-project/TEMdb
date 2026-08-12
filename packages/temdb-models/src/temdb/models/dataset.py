import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field

from .base import TEMDBModel

SizeClass = Literal["small", "medium", "large", "xlarge"]
DatasetStatus = Literal["collecting", "collected", "archived"]


class DatasetBase(TEMDBModel):
    description: str | None = Field(None, description="Human description of the dataset")
    specimen_id: str | None = Field(None, description="Specimen this dataset belongs to")
    size_class: SizeClass | None = Field(None, description="Planner size class; drives tile partitioning")
    estimated_tile_count: int | None = Field(None, description="Estimated total tiles; resolves size_class when set")
    metadata_json: dict[str, Any] | None = Field(None, description="Free-form metadata")


class DatasetCreate(DatasetBase):
    name: str = Field(..., description="Unique human-readable dataset name")
    parent_dataset_id: uuid.UUID | None = Field(None, description="Optional parent dataset (one level only)")
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class DatasetUpdate(TEMDBModel):
    description: str | None = None
    status: DatasetStatus | None = None
    size_class: SizeClass | None = None
    metadata_json: dict[str, Any] | None = None


class DatasetResponse(DatasetBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    dataset_id: uuid.UUID = Field(..., description="UUIDv7 primary key")
    name: str = Field(..., description="Unique human-readable dataset name")
    parent_dataset_id: uuid.UUID | None = Field(None, description="Parent dataset if this is a child (one level only)")
    status: DatasetStatus = Field(..., description="Lifecycle status")
    tile_hash_modulus: int | None = Field(None, description="System-managed frozen partition modulus")
    estimated_tile_count: int | None = Field(None, description="Estimated total tiles recorded at creation")
    collected_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
