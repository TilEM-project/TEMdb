from typing import List, Dict, Optional,Set
from beanie import Document
from pymongo import IndexModel, ASCENDING, DESCENDING
from pydantic import BaseModel
from datetime import datetime


class SpecimenUpdate(BaseModel):
    specimen_id: Optional[str] = None
    description: Optional[str] = None
    specimen_images: Optional[List[str]] = None
    functional_imaging_metadata: Optional[Dict] = None


class Specimen(Document):
    specimen_id: str
    description: Optional[str]
    specimen_images: Set[str]
    created_at: datetime
    updated_at: Optional[datetime]
    functional_imaging_metadata: Optional[Dict]

    class Settings:
        name = "specimens"
        indexes = [
            IndexModel([("specimen_id", ASCENDING)], unique=True, name="specimen_id_index"),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
        ]
