import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class DatasetSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "datasets"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, server_default=func.uuidv7(monotonic=True)
    )
    name: Mapped[str] = mapped_column(String, index=True, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    specimen_id: Mapped[str | None] = mapped_column(ForeignKey("specimens.specimen_id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="collecting")
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    size_class: Mapped[str] = mapped_column(String)
    # System-managed: NULL until the dataset's first tile partition is created,
    # then frozen to resolve_modulus(size_class). Never user-set.
    tile_hash_modulus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_tile_count: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
