from __future__ import annotations

from datetime import datetime
from typing import Any

from beanie.odm.fields import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from temdb.models import AcquisitionTaskStatus
from temdb.server.documents import AcquisitionTaskDocument


class AcquisitionTaskRead(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: PydanticObjectId = Field(..., alias="_id")
    task_id: str
    specimen_id: str
    block_id: str
    roi_id: str
    task_type: str
    version: int
    status: AcquisitionTaskStatus
    specimen_ref: PydanticObjectId | None
    block_ref: PydanticObjectId | None
    roi_ref: PydanticObjectId | None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def from_doc(cls, doc: AcquisitionTaskDocument) -> AcquisitionTaskRead:
        return cls(
            _id=doc.id,
            task_id=doc.task_id,
            specimen_id=doc.specimen_id,
            block_id=doc.block_id,
            roi_id=doc.roi_id,
            task_type=doc.task_type,
            version=doc.version,
            status=doc.status,
            specimen_ref=doc.specimen_ref,
            block_ref=doc.block_ref,
            roi_ref=doc.roi_ref,
            tags=getattr(doc, "tags", None),
            metadata=getattr(doc, "metadata", None),
            started_at=getattr(doc, "started_at", None),
            completed_at=getattr(doc, "completed_at", None),
            error_message=getattr(doc, "error_message", None),
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
