from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, ModelDumpMixin


class ROISQLModel(ModelDumpMixin, Base):
    __tablename__ = "rois"

    id: Mapped[int] = mapped_column(primary_key=True)
    roi_id: Mapped[str] = mapped_column(String, index=True, unique=True)
    roi_number: Mapped[int] = mapped_column(index=True)
    section_id: Mapped[str] = mapped_column(String, index=True)
    block_id: Mapped[str] = mapped_column(String, index=True)
    specimen_id: Mapped[str] = mapped_column(String, index=True)
    substrate_media_id: Mapped[str] = mapped_column(String, index=True)
    hierarchy_level: Mapped[int] = mapped_column(index=True)
    parent_roi_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    section_number: Mapped[int | None] = mapped_column(nullable=True, index=True)
    roi_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @classmethod
    def generate_roi_id(
        cls,
        specimen_id: str,
        block_id: str,
        section_id: str,
        substrate_media_id: str,
        roi_number: int,
        parent_roi_id: str | None = None,
    ) -> str:
        if parent_roi_id:
            return f"{parent_roi_id}.ROI{roi_number:04d}"
        return f"{specimen_id}.{block_id}.{section_id}.{substrate_media_id}.ROI{roi_number:03d}"

    @classmethod
    def parse_hierarchy_level(cls, roi_id: str) -> int:
        return roi_id.count(".ROI")
