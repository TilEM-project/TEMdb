from sqlalchemy import CheckConstraint, ForeignKey, Identity, Index, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class SubstrateSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "substrates"
    __table_args__ = (
        Index("ix_substrates_substrate_layout_id", "substrate_layout_id"),
        CheckConstraint(
            "aperture_status <@ ARRAY['available', 'used', 'damaged']::varchar[]", name="aperture_status_vocab"
        ),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    media_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    substrate_layout_id: Mapped[str] = mapped_column(ForeignKey("layouts.layout_id"))
    aperture_status: Mapped[list[str]] = mapped_column(ARRAY(String, zero_indexes=True))
