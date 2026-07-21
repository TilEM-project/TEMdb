from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class SectionSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("cutting_session_id", "section_number", name="uq_sections_session_number"),
        ForeignKeyConstraint(
            ["specimen_id", "block_id"], ["blocks.specimen_id", "blocks.block_id"], name="fk_sections_block"
        ),
        Index("ix_sections_specimen_block", "specimen_id", "block_id"),
        Index("ix_sections_barcode_nn", "barcode", postgresql_where=text("barcode IS NOT NULL")),
        CheckConstraint(
            "condition IN ('ok', 'damaged', 'destroyed', 'contaminated', 'lost')",
            name="condition_vocab",
        ),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    section_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    section_number: Mapped[int] = mapped_column()
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    cutting_session_id: Mapped[str] = mapped_column(ForeignKey("cutting_sessions.cutting_session_id"))
    block_id: Mapped[str] = mapped_column(String)
    specimen_id: Mapped[str] = mapped_column(String)
    media_id: Mapped[str] = mapped_column(ForeignKey("substrates.media_id"), index=True)
    optical_image: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    aperture_uid: Mapped[str | None] = mapped_column(String, nullable=True)
    aperture_index: Mapped[int | None] = mapped_column(nullable=True)
    barcode: Mapped[str | None] = mapped_column(String, nullable=True)
    condition: Mapped[str] = mapped_column(String, server_default=text("'ok'"))
    condition_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    section_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
