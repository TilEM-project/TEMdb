from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin


class BlockSQLModel(ModelDumpMixin, Base):
    __tablename__ = "blocks"
    __table_args__ = (UniqueConstraint("specimen_id", "block_id", name="uq_blocks_specimen_block"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[str] = mapped_column(String, index=True)
    specimen_id: Mapped[str] = mapped_column(ForeignKey("specimens.specimen_id"), index=True)
    microCT_info: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
