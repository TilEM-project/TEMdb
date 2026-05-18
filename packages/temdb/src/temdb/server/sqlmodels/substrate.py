from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin


class SubstrateSQLModel(ModelDumpMixin, Base):
    __tablename__ = "substrates"

    id: Mapped[int] = mapped_column(primary_key=True)
    media_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    media_type: Mapped[str] = mapped_column(String, index=True)
    uid: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True, index=True, default="new")
    refpoint: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    refpoint_world: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    source_path: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    apertures: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
