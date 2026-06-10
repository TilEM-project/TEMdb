import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Identity, Index, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
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
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    # unique=True (constraint, not separate index): the self-referential
    # replaces_acquisition_id FK needs the UNIQUE inside the same CREATE TABLE.
    acquisition_id: Mapped[str] = mapped_column(String, unique=True)
    montage_id: Mapped[str] = mapped_column(String)
    specimen_id: Mapped[str] = mapped_column(ForeignKey("specimens.specimen_id"), index=True)
    roi_id: Mapped[str] = mapped_column(ForeignKey("rois.roi_id"), index=True)
    acquisition_task_id: Mapped[str] = mapped_column(ForeignKey("acquisition_tasks.task_id"), index=True)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("datasets.dataset_id"), nullable=True
    )
    hardware_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    acquisition_settings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    calibration_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, default="imaging", index=True)
    tilt_angle: Mapped[float | None] = mapped_column(nullable=True)
    lens_correction: Mapped[bool | None] = mapped_column(nullable=True)
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
