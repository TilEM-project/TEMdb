from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin


class AcquisitionSQLModel(ModelDumpMixin, Base):
    __tablename__ = "acquisitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    acquisition_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    montage_id: Mapped[str] = mapped_column(String, index=True)
    specimen_id: Mapped[str] = mapped_column(String, index=True)
    roi_id: Mapped[str] = mapped_column(String, index=True)
    acquisition_task_id: Mapped[str] = mapped_column(String, index=True)
    hardware_settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    acquisition_settings: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    calibration_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
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
    storage_locations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    montage_set_name: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    sub_region: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    replaces_acquisition_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
