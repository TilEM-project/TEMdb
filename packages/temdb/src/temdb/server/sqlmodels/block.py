from typing import Any

from sqlalchemy import ForeignKey, Identity, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class BlockSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "blocks"
    __table_args__ = (UniqueConstraint("specimen_id", "block_id", name="uq_blocks_specimen_block"),)

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    block_id: Mapped[str] = mapped_column(String)
    specimen_id: Mapped[str] = mapped_column(ForeignKey("specimens.specimen_id"))
    microCT_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
