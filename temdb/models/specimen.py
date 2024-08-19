from typing import List, Dict, Optional
from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING
from pydantic import BaseModel
from datetime import datetime


class SpecimenUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    specimen_images: Optional[List[str]] = None
    functional_imaging_metadata: Optional[Dict] = None


class Specimen(Document):
    name: str
    description: str
    specimen_images: List[str]
    created_at: datetime
    updated_at: Optional[datetime]
    functional_imaging_metadata: Optional[Dict]

    class Settings:
        name = "specimens"
        indexes = [
            IndexModel([("name", ASCENDING)], unique=True, name="name_index"),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
        ]
