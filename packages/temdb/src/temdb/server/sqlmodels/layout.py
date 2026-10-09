from typing import Any

from sqlalchemy import Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class SubstrateLayoutSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "layouts"
    __table_args__ = (Index("layout_id", "media_type", "name"),)

    layout_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    fiducials: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    apertures: Mapped[dict[int, Any] | None] = mapped_column(JSONB, nullable=True)
    media_type: Mapped[str] = mapped_column(String)
