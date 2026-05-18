from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin


class TileSQLModel(ModelDumpMixin, Base):
    __tablename__ = "tiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    tile_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    acquisition_id: Mapped[str] = mapped_column(String, index=True)
    raster_index: Mapped[int] = mapped_column(index=True)
    stage_position: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    raster_position: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    focus_score: Mapped[float]
    min_value: Mapped[float]
    max_value: Mapped[float]
    mean_value: Mapped[float]
    std_value: Mapped[float]
    image_path: Mapped[str] = mapped_column(String)
    matcher: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    supertile_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    supertile_raster_position: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
