from typing import Any

from sqlalchemy import Identity, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class SubstrateSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "substrates"
    __table_args__ = (Index("ix_substrates_media_type_status", "media_type", "status"),)

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    media_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    media_type: Mapped[str] = mapped_column(String)
    uid: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True, default="new")
    refpoint: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    refpoint_world: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    source_path: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True)
    apertures: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
