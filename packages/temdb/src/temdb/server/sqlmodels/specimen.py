from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin


class SpecimenSQLModel(ModelDumpMixin, Base):
    __tablename__ = "specimens"

    id: Mapped[int] = mapped_column(primary_key=True)
    specimen_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    specimen_images: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    functional_imaging_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
