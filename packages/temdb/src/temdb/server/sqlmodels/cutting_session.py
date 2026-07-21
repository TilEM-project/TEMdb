from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, Identity, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class CuttingSessionSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "cutting_sessions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["specimen_id", "block_id"], ["blocks.specimen_id", "blocks.block_id"], name="fk_cutting_sessions_block"
        ),
        Index("ix_cutting_sessions_specimen_block", "specimen_id", "block_id"),
    )

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    cutting_session_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    specimen_id: Mapped[str] = mapped_column(String)
    block_id: Mapped[str] = mapped_column(String)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operator: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    sectioning_device: Mapped[str] = mapped_column(String)
    media_type: Mapped[str] = mapped_column(String)
    knife_id: Mapped[str | None] = mapped_column(String, nullable=True)
