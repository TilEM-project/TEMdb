import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import REAL, DateTime, ForeignKey, Index, Integer, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin


class TileSQLModel(ModelDumpMixin, Base):
    __tablename__ = "tiles"
    __table_args__ = (
        Index("ix_tiles_supertile_id_nn", "supertile_id", postgresql_where=text("supertile_id IS NOT NULL")),
        Index(
            "ix_tiles_focus_score_nn",
            "dataset_id",
            "focus_score",
            postgresql_where=text("focus_score IS NOT NULL"),
        ),
        {"postgresql_partition_by": "LIST (dataset_id)"},
    )

    # Composite PK: includes every partition-key column (dataset_id at the LIST
    # level, acquisition_id at the HASH level). raster_index makes the row
    # unique within an acquisition's montage (row/col are not cross-ROI unique).
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("datasets.dataset_id"), primary_key=True
    )
    acquisition_id: Mapped[str] = mapped_column(String, primary_key=True)
    raster_index: Mapped[int] = mapped_column(Integer, primary_key=True)

    tile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), index=True, server_default=func.uuidv7(monotonic=True)
    )
    stage_x_nm: Mapped[float] = mapped_column(nullable=False)
    stage_y_nm: Mapped[float] = mapped_column(nullable=False)
    montage_row: Mapped[int] = mapped_column(Integer, nullable=False)
    montage_col: Mapped[int] = mapped_column(Integer, nullable=False)
    focus_score: Mapped[float | None] = mapped_column(REAL, nullable=True)
    min_value: Mapped[float | None] = mapped_column(REAL, nullable=True)
    max_value: Mapped[float | None] = mapped_column(REAL, nullable=True)
    mean_value: Mapped[float | None] = mapped_column(REAL, nullable=True)
    std_value: Mapped[float | None] = mapped_column(REAL, nullable=True)

    image_path: Mapped[str] = mapped_column(String, nullable=False)
    matcher: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    supertile_id: Mapped[str | None] = mapped_column(String, nullable=True)
    supertile_raster_position: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    # Write-once table: created_at only, no updated_at.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
