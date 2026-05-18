from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin


class CuttingSessionSQLModel(ModelDumpMixin, Base):
    __tablename__ = "cutting_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    cutting_session_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    specimen_id: Mapped[str] = mapped_column(String, index=True)
    block_id: Mapped[str] = mapped_column(String, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operator: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    sectioning_device: Mapped[str] = mapped_column(String)
    media_type: Mapped[str] = mapped_column(String, index=True)
    knife_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
