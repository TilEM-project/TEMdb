from typing import Any

from sqlalchemy import Identity, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class SubstrateLayoutSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "layouts"
    __table_args__ = (Index("layout_id", "media_type", "status"),)

    layout_id: Mapped[str] = mapped_column(Identity(always=True), primary_key=True)
    fiducials: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    apertures: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    media_type: Mapped[str | None] = mapped_column(String, nullable=True)
