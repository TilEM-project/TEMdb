from __future__ import annotations

from datetime import datetime

from beanie.odm.fields import PydanticObjectId
from pydantic import ConfigDict, Field

from temdb.models import ROIBase
from temdb.server.documents import ROIDocument


class ROIRead(ROIBase):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: PydanticObjectId = Field(..., alias="_id")
    roi_id: str
    roi_number: int
    section_id: str
    block_id: str
    specimen_id: str
    substrate_media_id: str
    hierarchy_level: int
    section_ref: PydanticObjectId | None
    parent_roi_ref: PydanticObjectId | None
    section_number: int | None = None
    is_parent: bool = False
    updated_at: datetime | None = None

    @classmethod
    def from_doc(cls, doc: ROIDocument) -> ROIRead:
        base_fields = ROIBase.model_fields.keys()
        extras = {k: getattr(doc, k, None) for k in base_fields if hasattr(doc, k)}
        return cls(
            _id=doc.id,
            roi_id=doc.roi_id,
            roi_number=doc.roi_number,
            section_id=doc.section_id,
            block_id=doc.block_id,
            specimen_id=doc.specimen_id,
            substrate_media_id=doc.substrate_media_id,
            hierarchy_level=doc.hierarchy_level,
            section_ref=doc.section_ref,
            parent_roi_ref=doc.parent_roi_ref,
            section_number=doc.section_number,
            is_parent=doc.is_parent,
            updated_at=doc.updated_at,
            **extras,
        )
