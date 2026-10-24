import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import ConfigDict, Field

from .base import TEMDBRecord
from .file_storage import StorageDefault

SizeClass = Literal["small", "medium", "large", "xlarge"]
DatasetStatus = Literal["collecting", "collected", "archived"]


class DatasetBase(TEMDBRecord):
    description: str | None = Field(None, description="Human description of the dataset")
    specimen_id: str | None = Field(None, description="Specimen this dataset belongs to")
    size_class: SizeClass | None = Field(None, description="Planner size class; drives tile partitioning")
    default_storage: StorageDefault | None = Field(None, description="Default storage for tiles in this dataset")
    estimated_tile_count: int | None = Field(
        None, ge=0, description="Estimated total tiles; resolves size_class when set"
    )
    metadata_json: dict[str, Any] | None = Field(None, description="Free-form metadata")


class DatasetCreate(DatasetBase):
    name: str = Field(..., description="Unique human-readable dataset name")
    parent_dataset_id: uuid.UUID | None = Field(None, description="Optional parent dataset (one level only)")
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class DatasetUpdate(TEMDBRecord):
    description: str | None = Field(None, description="Human description of the dataset")
    status: DatasetStatus = Field(None, description="Lifecycle status")
    size_class: SizeClass = Field(None, description="Planner size class; drives tile partitioning")
    metadata_json: dict[str, Any] | None = Field(None, description="Free-form metadata")


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
