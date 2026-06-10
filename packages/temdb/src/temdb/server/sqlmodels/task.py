import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    String,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class AcquisitionTaskSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "acquisition_tasks"
    __table_args__ = (
        ForeignKeyConstraint(["specimen_id", "block_id"], ["blocks.specimen_id", "blocks.block_id"]),
        Index("ix_acquisition_tasks_specimen_block", "specimen_id", "block_id"),
        Index("ix_acquisition_tasks_dataset_id_nn", "dataset_id", postgresql_where=text("dataset_id IS NOT NULL")),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    task_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    specimen_id: Mapped[str] = mapped_column(String)
    block_id: Mapped[str] = mapped_column(String)
    roi_id: Mapped[str] = mapped_column(ForeignKey("rois.roi_id"), index=True)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("datasets.dataset_id"), nullable=True
    )
    task_type: Mapped[str] = mapped_column(String, default="standard_acquisition")
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String, default="planned", index=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
