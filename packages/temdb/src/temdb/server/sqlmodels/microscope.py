import uuid

from sqlalchemy import String, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class MicroscopeSQLModel(ModelDumpMixin, TimestampMixin, Base):
    __tablename__ = "microscopes"

    microscope_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.uuidv7(monotonic=True),
    )
    label: Mapped[str] = mapped_column(String, unique=True)
    microscope_type: Mapped[str] = mapped_column(String, server_default=text("'TEM'"))
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
