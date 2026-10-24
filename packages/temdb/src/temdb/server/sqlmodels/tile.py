import re
import uuid
from typing import Any

from sqlalchemy import REAL, ForeignKey, ForeignKeyConstraint, Index, Integer, SmallInteger, String, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


def format_tile_id(montage_id: str, row: int, col: int, retake: int) -> str:
    tile_id = f"{montage_id}_r{row:03d}_c{col:03d}"
    return f"{tile_id}_a{retake}" if retake else tile_id


def parse_tile_id(montage_id: str, tile_id: str) -> tuple[int, int, int] | None:
    match = re.fullmatch(rf"{re.escape(montage_id)}_r(\d+)_c(\d+)(?:_a(\d+))?", tile_id)
    if match is None:
        return None
    key = (int(match[1]), int(match[2]), int(match[3] or 0))
    if format_tile_id(montage_id, *key) != tile_id or max(key) > 32767:
        return None
    return key


class TileSQLModel(ModelDumpMixin, TimestampMixin, Base):
    __tablename__ = "tiles"
    __table_args__ = (
        Index("ix_tiles_supertile_id_nn", "supertile_id", postgresql_where=text("supertile_id IS NOT NULL")),
        Index(
            "ix_tiles_focus_score_nn",
            "dataset_id",
            "focus_score",
            postgresql_where=text("focus_score IS NOT NULL"),
        ),
        ForeignKeyConstraint(
            ["dataset_id", "run_id"],
            ["acquisitions.dataset_id", "acquisitions.run_id"],
            name="fk_tiles_dataset_id_acquisitions",
        ),
        {"postgresql_partition_by": "LIST (dataset_id)"},
    )

    # The PK holds every partition-key column (dataset_id at the LIST level, run_id at the HASH level).
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("datasets.dataset_id"), primary_key=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    row: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    col: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    retake: Mapped[int] = mapped_column(SmallInteger, primary_key=True, server_default=text("0"))

    raster_index: Mapped[int] = mapped_column(Integer, nullable=False)
    stage_x_nm: Mapped[float] = mapped_column(nullable=False)
    stage_y_nm: Mapped[float] = mapped_column(nullable=False)
    stage_z_nm: Mapped[float | None] = mapped_column(nullable=True)
    focus_score: Mapped[float | None] = mapped_column(REAL, nullable=True)
    min_value: Mapped[float | None] = mapped_column(REAL, nullable=True)
    max_value: Mapped[float | None] = mapped_column(REAL, nullable=True)
    mean_value: Mapped[float | None] = mapped_column(REAL, nullable=True)
    std_value: Mapped[float | None] = mapped_column(REAL, nullable=True)

    image: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    matcher: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    supertile_id: Mapped[str | None] = mapped_column(String, nullable=True)
    supertile_raster_position: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Base gives every table an extra column; tiles have none.
    extra = None
