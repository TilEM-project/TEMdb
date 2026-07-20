import uuid
from typing import Any

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Identity, Index, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class ROISQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "rois"
    __table_args__ = (
        ForeignKeyConstraint(["specimen_id", "block_id"], ["blocks.specimen_id", "blocks.block_id"]),
        Index("ix_rois_specimen_block", "specimen_id", "block_id"),
        Index("ix_rois_parent_roi_id_nn", "parent_roi_id", postgresql_where=text("parent_roi_id IS NOT NULL")),
        Index("ix_rois_dataset_id_nn", "dataset_id", postgresql_where=text("dataset_id IS NOT NULL")),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    # unique=True (constraint, not separate index): the self-referential
    # parent_roi_id FK needs the UNIQUE inside the same CREATE TABLE.
    roi_id: Mapped[str] = mapped_column(String, unique=True)
    roi_number: Mapped[int] = mapped_column()
    section_id: Mapped[str] = mapped_column(ForeignKey("sections.section_id"), index=True)
    block_id: Mapped[str] = mapped_column(String)
    specimen_id: Mapped[str] = mapped_column(String)
    substrate_media_id: Mapped[str] = mapped_column(ForeignKey("substrates.media_id"), index=True)
    hierarchy_level: Mapped[int] = mapped_column()
    parent_roi_id: Mapped[str | None] = mapped_column(ForeignKey("rois.roi_id"), nullable=True)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("datasets.dataset_id"), nullable=True
    )
    section_number: Mapped[int | None] = mapped_column(nullable=True)
    roi_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    @classmethod
    def generate_roi_id(
        cls,
        specimen_id: str,
        block_id: str,
        section_id: str,
        substrate_media_id: str,
        roi_number: int,
        parent_roi_id: str | None = None,
    ) -> str:
        if parent_roi_id:
            return f"{parent_roi_id}.ROI{roi_number:04d}"
        return f"{specimen_id}.{block_id}.{section_id}.{substrate_media_id}.ROI{roi_number:03d}"

    @classmethod
    def parse_hierarchy_level(cls, roi_id: str) -> int:
        return roi_id.count(".ROI")
