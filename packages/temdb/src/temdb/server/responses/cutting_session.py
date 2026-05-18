from __future__ import annotations

from datetime import datetime

from beanie.odm.fields import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from temdb.server.documents import CuttingSessionDocument


class CuttingSessionRead(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: PydanticObjectId = Field(..., alias="_id")
    cutting_session_id: str
    specimen_id: str
    block_id: str
    start_time: datetime
    end_time: datetime | None = None
    operator: str | None = None
    sectioning_device: str
    media_type: str
    knife_id: str | None = None
    specimen_ref: PydanticObjectId | None
    block_ref: PydanticObjectId | None
    created_at: datetime
    updated_at: datetime | None

    @classmethod
    def from_doc(cls, doc: CuttingSessionDocument) -> CuttingSessionRead:
        return cls(
            _id=doc.id,
            cutting_session_id=doc.cutting_session_id,
            specimen_id=doc.specimen_id,
            block_id=doc.block_id,
            start_time=doc.start_time,
            end_time=getattr(doc, "end_time", None),
            operator=getattr(doc, "operator", None),
            sectioning_device=doc.sectioning_device,
            media_type=doc.media_type,
            knife_id=getattr(doc, "knife_id", None),
            specimen_ref=doc.specimen_ref,
            block_ref=doc.block_ref,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
