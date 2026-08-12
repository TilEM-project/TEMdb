import uuid
from datetime import datetime
from typing import Any

from pydantic import AliasChoices, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from temdb.models.base import TEMDBModel
from temdb.models.enums import TASK_KINDS


class AcquisitionTaskBase(TEMDBModel):
    """Base acquisition task fields."""

    kind: str | None = Field(None, description="Task kind: montage or lens_correction")
    task_group_id: uuid.UUID | None = Field(None, description="Group ID linking related tasks (e.g., a tilt series)")
    tilt_angle_deg: float | None = Field(None, description="Planned tilt angle in degrees")
    sub_region: dict[str, Any] | None = Field(None, description="Planned sub-region of the ROI")
    tags: list[str] | None = Field(None, description="Tags for filtering")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class AcquisitionTaskCreate(AcquisitionTaskBase):
    """Schema for creating an acquisition task."""

    task_id: str = Field(..., description="Unique identifier for this task")
    specimen_id: str | None = Field(None, description="ID of specimen (required unless kind='lens_correction')")
    block_id: str | None = Field(None, description="ID of block (required unless kind='lens_correction')")
    roi_id: str | None = Field(None, description="ID of ROI to acquire (required unless kind='lens_correction')")
    kind: str = Field(default="montage", description="Task kind: montage or lens_correction")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")

    @model_validator(mode="after")
    def _validate_kind_and_lineage(self) -> "AcquisitionTaskCreate":
        if self.kind not in TASK_KINDS:
            raise PydanticCustomError("value_error", f"kind must be one of {TASK_KINDS}")
        if self.kind != "lens_correction" and not (self.roi_id and self.specimen_id and self.block_id):
            raise PydanticCustomError(
                "value_error",
                "specimen_id, block_id, and roi_id are required unless kind='lens_correction'",
            )
        return self


class AcquisitionTaskUpdate(AcquisitionTaskBase):
    """Schema for updating an acquisition task."""

    @model_validator(mode="after")
    def _validate_kind(self) -> "AcquisitionTaskUpdate":
        if self.kind is not None and self.kind not in TASK_KINDS:
            raise PydanticCustomError("value_error", f"kind must be one of {TASK_KINDS}")
        return self


class AcquisitionTaskResponse(AcquisitionTaskBase):
    """Schema for acquisition task API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Internal integer primary key")
    task_id: str = Field(..., description="Unique identifier for this task")
    specimen_id: str | None = Field(None, description="ID of specimen")
    block_id: str | None = Field(None, description="ID of block")
    roi_id: str | None = Field(None, description="ID of region of interest")
    kind: str = Field(..., description="Task kind: montage or lens_correction")
    status: str | None = Field(None, description="Task state derived from runs (ADR 0011)")
    superseded_by: str | None = Field(None, description="task_id of the replacement task, if superseded")
    dataset_id: uuid.UUID | None = Field(None, description="Dataset this task belongs to (UUIDv7)")
    metadata: dict[str, Any] | None = Field(
        None,
        description="Additional metadata",
        validation_alias=AliasChoices("metadata_json", "metadata"),
    )

    created_at: datetime | None = None
    updated_at: datetime | None = None
