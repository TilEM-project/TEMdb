import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, desc, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class LensCorrectionSQLModel(ModelDumpMixin, TimestampMixin, Base):
    __tablename__ = "lens_corrections"

    lc_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.uuidv7(monotonic=True),
    )
    microscope_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("microscopes.microscope_id"),
    )
    magnification: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_run_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    source_dataset_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    shared_transform: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    correction_x_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    correction_y_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    solver_params: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_lens_corrections_microscope_mag",
              "microscope_id", "magnification", desc("started_at")),
    )
