from sqlalchemy import Identity, String, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin, TimestampMixin


class MicroscopeSQLModel(ModelDumpMixin, TimestampMixin, Base):
    __tablename__ = "microscopes"

    id: Mapped[int] = mapped_column(Identity(always=True), primary_key=True)
    microscope_id: Mapped[str] = mapped_column(String, unique=True)
    microscope_type: Mapped[str] = mapped_column(String, server_default=text("'TEM'"))
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
