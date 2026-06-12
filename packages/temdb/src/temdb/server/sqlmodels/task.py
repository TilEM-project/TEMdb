import uuid
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    String,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class AcquisitionTaskSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "acquisition_tasks"
    __table_args__ = (
        ForeignKeyConstraint(["specimen_id", "block_id"], ["blocks.specimen_id", "blocks.block_id"]),
        Index("ix_acquisition_tasks_specimen_block", "specimen_id", "block_id"),
        Index("ix_acquisition_tasks_dataset_id_nn", "dataset_id", postgresql_where=text("dataset_id IS NOT NULL")),
        Index(
            "ix_acquisition_tasks_superseded_nn",
            "superseded_by",
            postgresql_where=text("superseded_by IS NOT NULL"),
        ),
        Index(
            "ix_acquisition_tasks_task_group_nn",
            "task_group_id",
            postgresql_where=text("task_group_id IS NOT NULL"),
        ),
        CheckConstraint(
            "kind = 'lens_correction' OR (roi_id IS NOT NULL AND specimen_id IS NOT NULL AND block_id IS NOT NULL)",
            name="lineage_required_for_montage",
        ),
        CheckConstraint("kind IN ('montage', 'lens_correction')", name="kind_vocab"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    task_id: Mapped[str] = mapped_column(String, unique=True)
    specimen_id: Mapped[str | None] = mapped_column(String, nullable=True)
    block_id: Mapped[str | None] = mapped_column(String, nullable=True)
    roi_id: Mapped[str | None] = mapped_column(ForeignKey("rois.roi_id"), index=True, nullable=True)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("datasets.dataset_id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String, server_default=text("'montage'"))
    superseded_by: Mapped[str | None] = mapped_column(String, ForeignKey("acquisition_tasks.task_id"), nullable=True)
    task_group_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    tilt_angle_deg: Mapped[float | None] = mapped_column(nullable=True)
    sub_region: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
