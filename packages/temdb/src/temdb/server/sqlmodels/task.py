from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin


class AcquisitionTaskSQLModel(ModelDumpMixin, Base):
    __tablename__ = "acquisition_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    specimen_id: Mapped[str] = mapped_column(String, index=True)
    block_id: Mapped[str] = mapped_column(String, index=True)
    roi_id: Mapped[str] = mapped_column(String, index=True)
    task_type: Mapped[str] = mapped_column(String, default="standard_acquisition", index=True)
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String, default="planned", index=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
