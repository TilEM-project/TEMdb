from typing import Any

from sqlalchemy import Identity, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class SpecimenSQLModel(TimestampMixin, ModelDumpMixin, Base):
    __tablename__ = "specimens"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    specimen_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    specimen_images: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    functional_imaging_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
