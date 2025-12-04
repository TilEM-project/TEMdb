from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SpecimenBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    description: str | None = Field(None, description="Description of specimen, used for additional notes.")
    specimen_images: set[str] | None = Field(None, description="Images of specimen")
    functional_imaging_metadata: dict[str, Any] | None = Field(
        None,
        description="Functional imaging metadata of specimen, optional links to other datasets",
    )


class SpecimenCreate(SpecimenBase):
    specimen_id: str = Field(..., description="Unique specimen identifier")


class SpecimenUpdate(SpecimenBase):
    pass


class SpecimenResponse(SpecimenBase):
    specimen_id: str = Field(..., description="Unique specimen identifier")

    created_at: datetime | None = None
    updated_at: datetime | None = None
