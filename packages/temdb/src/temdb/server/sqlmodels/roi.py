import uuid
from typing import Any

from sqlalchemy import ForeignKey, Identity, Index, String, UniqueConstraint, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class ROISQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "rois"
    __table_args__ = (
        UniqueConstraint(
            "substrate_media_id",
            "aperture_index",
            "created_at",
            name="uq_rois_drawn",
            postgresql_nulls_not_distinct=True,
        ),
        UniqueConstraint(
            "substrate_media_id",
            "aperture_index",
            "roi_number",
            name="uq_rois_number",
            postgresql_nulls_not_distinct=True,
        ),
        Index("ix_rois_parent_roi_id_nn", "parent_roi_id", postgresql_where=text("parent_roi_id IS NOT NULL")),
        Index("ix_rois_dataset_id_nn", "dataset_id", postgresql_where=text("dataset_id IS NOT NULL")),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    # unique=True (constraint, not separate index): the self-referential
    # parent_roi_id FK needs the UNIQUE inside the same CREATE TABLE.
    roi_id: Mapped[str] = mapped_column(String, unique=True)
    roi_number: Mapped[int] = mapped_column()
    section_id: Mapped[str] = mapped_column(ForeignKey("sections.section_id"), index=True)
    substrate_media_id: Mapped[str] = mapped_column(ForeignKey("substrates.media_id"), index=True)
    aperture_index: Mapped[int | None] = mapped_column(nullable=True)
    parent_roi_id: Mapped[str | None] = mapped_column(ForeignKey("rois.roi_id"), nullable=True)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("datasets.dataset_id"), nullable=True
    )
    roi_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
