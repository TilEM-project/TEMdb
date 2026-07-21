from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from .base import TEMDBModel
from .utils.uri import URI


class SpecimenBase(TEMDBModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    description: str | None = Field(None, description="Description of specimen, used for additional notes.")
    specimen_images: set[URI.Type] | None = Field(None, description="Images of specimen")
    functional_imaging_metadata: dict[str, Any] | None = Field(
        None,
        description="Functional imaging metadata of specimen, optional links to other datasets",
    )


class SpecimenCreate(SpecimenBase):
    specimen_id: str = Field(..., description="Unique specimen identifier")
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class SpecimenUpdate(SpecimenBase):
    pass


class SpecimenResponse(SpecimenBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int
    specimen_id: str = Field(..., description="Unique specimen identifier")

    created_at: datetime | None = None
    updated_at: datetime | None = None
