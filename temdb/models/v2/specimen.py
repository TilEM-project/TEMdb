from typing import List, Dict, Optional, Set
from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class SpecimenBase(BaseModel):
    description: Optional[str] = Field(
        None, description="Description of specimen, used for additional notes."
    )
    specimen_images: Optional[List[str]] = Field(None, description="Images of specimen")
    functional_imaging_metadata: Optional[Dict] = Field(
        None,
        description="Functional imaging metadata of specimen, optional links to other datasets",
    )


class SpecimenCreate(SpecimenBase):
    specimen_id: str = Field(..., description="ID of specimen")
    created_at: datetime = Field(
        ..., description="Time when specimen metadata was created"
    )


class SpecimenUpdate(SpecimenBase):
    specimen_id: Optional[str] = Field(None, description="ID of specimen")


class Specimen(Document):
    specimen_id: str = Field(..., description="ID of specimen")
    description: Optional[str] = Field(
        None, description="Description of specimen, used for additional notes."
    )
    specimen_images: Optional[Set[str]] = Field(None, description="Images of specimen")
    created_at: datetime = Field(
        ..., description="Time when specimen metadata was created"
    )
    updated_at: Optional[datetime] = Field(
        None, description="Time when specimen metadata was last updated"
    )
    functional_imaging_metadata: Optional[Dict] = Field(
        None,
        description="Functional imaging metadata of specimen, optional links to other datasets",
    )

    class Settings:
        name = "specimens"
        indexes = [
            IndexModel(
                [("specimen_id", ASCENDING)], unique=True, name="specimen_id_index"
            ),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
        ]
