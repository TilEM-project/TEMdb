from __future__ import annotations

from datetime import datetime

from beanie.odm.fields import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from temdb.server.documents import SectionDocument


class SectionRead(BaseModel):
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
    section_metrics: dict | None = None
    barcode: str | None = None
    aperture_index: int | None = None
    aperture_uid: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def from_doc(cls, doc: SectionDocument) -> SectionRead:
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
            section_metrics=(
                doc.section_metrics.model_dump() if doc.section_metrics is not None else None
            ),
            barcode=getattr(doc, "barcode", None),
            aperture_index=getattr(doc, "aperture_index", None),
            aperture_uid=getattr(doc, "aperture_uid", None),
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
