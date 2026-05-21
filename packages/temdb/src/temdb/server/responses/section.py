from __future__ import annotations

from datetime import datetime

from beanie.odm.fields import PydanticObjectId
from pydantic import ConfigDict, Field

from temdb.models import SectionBase
from temdb.server.documents import SectionDocument


class SectionRead(SectionBase):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: PydanticObjectId = Field(..., alias="_id")
    section_id: str
    section_number: int
    timestamp: datetime
    cutting_session_id: str
    block_id: str
    specimen_id: str
    media_id: str
    cutting_session_ref: PydanticObjectId | None
    substrate_ref: PydanticObjectId | None
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def from_doc(cls, doc: SectionDocument) -> SectionRead:
        explicit = {
            "section_id",
            "section_number",
            "timestamp",
            "cutting_session_id",
            "block_id",
            "specimen_id",
            "media_id",
            "cutting_session_ref",
            "substrate_ref",
            "created_at",
            "updated_at",
        }
        base_extras = {
            k: getattr(doc, k, None)
            for k in SectionBase.model_fields
            if k not in explicit and hasattr(doc, k)
        }
        return cls(
            _id=doc.id,
            section_id=doc.section_id,
            section_number=doc.section_number,
            timestamp=doc.timestamp,
            cutting_session_id=doc.cutting_session_id,
            block_id=doc.block_id,
            specimen_id=doc.specimen_id,
            media_id=doc.media_id,
            cutting_session_ref=doc.cutting_session_ref,
            substrate_ref=doc.substrate_ref,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
            **base_extras,
        )
