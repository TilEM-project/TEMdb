from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin


class SectionSQLModel(ModelDumpMixin, Base):
    __tablename__ = "sections"
    __table_args__ = (UniqueConstraint("cutting_session_id", "section_number", name="uq_sections_session_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    section_number: Mapped[int] = mapped_column(index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    cutting_session_id: Mapped[str] = mapped_column(String, index=True)
    block_id: Mapped[str] = mapped_column(String, index=True)
    specimen_id: Mapped[str] = mapped_column(String, index=True)
    media_id: Mapped[str] = mapped_column(String, index=True)
    optical_image: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    aperture_uid: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    aperture_index: Mapped[int | None] = mapped_column(nullable=True, index=True)
    barcode: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    section_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
