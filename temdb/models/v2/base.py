from datetime import datetime

from beanie import Document
from pydantic import Field


class BaseDocument(Document):
    code: str = Field(..., description="Unique identifier for this record")
    name: str = Field(None, description="Optional human-friendly name")
    created_at: datetime
    updated_at: datetime