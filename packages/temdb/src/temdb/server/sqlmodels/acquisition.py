import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    REAL,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class AcquisitionSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "acquisitions"
    __table_args__ = (
        Index("ix_acquisitions_dataset_id_nn", "dataset_id", postgresql_where=text("dataset_id IS NOT NULL")),
        Index(
            "ix_acquisitions_montage_set_name_nn",
            "montage_set_name",
            postgresql_where=text("montage_set_name IS NOT NULL"),
        ),
        Index(
            "ix_acquisitions_replaces_nn",
            "replaces_acquisition_id",
            postgresql_where=text("replaces_acquisition_id IS NOT NULL"),
        ),
        Index("ix_acquisitions_lc_id_nn", "lc_id", postgresql_where=text("lc_id IS NOT NULL")),
        Index("ix_acquisitions_dataset_kind_qc", "dataset_id", "kind", "qc_state"),
        CheckConstraint("status IS NULL OR status IN ('complete', 'aborted', 'failed')", name="status_vocab"),
        CheckConstraint("(status IS NULL) = (end_time IS NULL)", name="status_terminal_consistency"),
        CheckConstraint("qc_state IN ('pending', 'qc_pass', 'qc_fail', 'needs_review')", name="qc_state_vocab"),
        CheckConstraint(
            "transfer_state IN ('not_started', 'in_progress', 'complete', 'error')", name="transfer_state_vocab"
        ),
        CheckConstraint("kind IN ('montage', 'lens_correction')", name="kind_vocab"),
        CheckConstraint(
            "kind = 'lens_correction' OR (roi_id IS NOT NULL AND specimen_id IS NOT NULL)",
            name="lineage_required_for_montage",
        ),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    # unique=True (constraint, not separate index): the self-referential
    # replaces_acquisition_id FK needs the UNIQUE inside the same CREATE TABLE.
    acquisition_id: Mapped[str] = mapped_column(String, unique=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), unique=True, server_default=func.uuidv7(monotonic=True)
    )
    montage_id: Mapped[str] = mapped_column(String)
    specimen_id: Mapped[str | None] = mapped_column(ForeignKey("specimens.specimen_id"), index=True, nullable=True)
    roi_id: Mapped[str | None] = mapped_column(ForeignKey("rois.roi_id"), index=True, nullable=True)
    acquisition_task_id: Mapped[str] = mapped_column(ForeignKey("acquisition_tasks.task_id"), index=True)
    microscope_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("microscopes.microscope_id"))
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("datasets.dataset_id"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String, server_default=text("'montage'"))
    lc_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("lens_corrections.lc_id"), nullable=True
    )
    hardware_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    acquisition_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    calibration_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    qc_state: Mapped[str] = mapped_column(String, server_default=text("'pending'"))
    qc_state_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    qc_state_updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    transfer_state: Mapped[str] = mapped_column(String, server_default=text("'not_started'"))
    transfer_state_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transfer_state_updated_by: Mapped[str | None] = mapped_column(String, nullable=True)
    tile_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_focus_score: Mapped[float | None] = mapped_column(REAL, nullable=True)
    failed_tile_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    median_match_quality: Mapped[float | None] = mapped_column(REAL, nullable=True)
    tilt_angle_deg: Mapped[float | None] = mapped_column(nullable=True)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        default=lambda: datetime.now(timezone.utc),
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    storage_locations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    montage_set_name: Mapped[str | None] = mapped_column(String, nullable=True)
    sub_region: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    replaces_acquisition_id: Mapped[str | None] = mapped_column(
        ForeignKey("acquisitions.acquisition_id"), nullable=True
    )
