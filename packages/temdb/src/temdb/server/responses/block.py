from __future__ import annotations

from datetime import datetime

from beanie.odm.fields import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from temdb.server.documents import BlockDocument


class BlockRead(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: PydanticObjectId = Field(..., alias="_id")
    block_id: str
    specimen_id: str
    specimen_ref: PydanticObjectId | None
    description: str | None = None
    microCT_info: dict | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def from_doc(cls, doc: BlockDocument) -> BlockRead:
        return cls(
            _id=doc.id,
            block_id=doc.block_id,
            specimen_id=doc.specimen_id,
            specimen_ref=doc.specimen_ref,
            description=doc.description,
            microCT_info=getattr(doc, "microCT_info", None),
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
