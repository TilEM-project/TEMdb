from sqlalchemy import ForeignKey, Identity, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class SubstrateSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "substrates"
    __table_args__ = (Index("ix_substrates_substrate_layout_id", "substrate_layout_id"),)

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    media_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    condition: Mapped[dict[int, str]] = mapped_column(JSONB, nullable=True)
    substrate_layout_id: Mapped[str] = mapped_column(ForeignKey("layouts.layout_id"))
