from datetime import datetime

from beanie import Document, Link
from pydantic import Field
from pymongo import ASCENDING, IndexModel
from temdb.models import ROIBase

from .section import SectionDocument


class ROIDocument(Document, ROIBase):
    """MongoDB document for ROI data."""

    roi_id: str = Field(
        ...,
        description="Hierarchical, globally unique ID (e.g., 'SPEC001.BLK001.SEC001.SUB001.ROI001')",
    )
    roi_number: int = Field(
        ...,
        description="Sequential number for this ROI within its parent context",
    )
    section_id: str = Field(..., description="Human-readable ID of the parent Section")
    block_id: str = Field(..., description="Human-readable ID of the parent Block")
    specimen_id: str = Field(..., description="Human-readable ID of the parent Specimen")
    substrate_media_id: str = Field(..., description="Media ID of the substrate this section is placed on")
    hierarchy_level: int = Field(
        ...,
        description="Depth level in ROI hierarchy (1=top-level section ROI, 2=child ROI, etc.)",
    )

    section_ref: Link[SectionDocument] = Field(..., description="Internal link to the section document")
    parent_roi_ref: Link["ROIDocument"] | None = Field(
        None, description="Internal link to the parent ROI document, if any"
    )

    section_number: int | None = Field(None)
    updated_at: datetime | None = Field(None, description="Time of last update")

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
        """Generate hierarchical ROI ID including substrate."""
        if parent_roi_id:
            return f"{parent_roi_id}.ROI{roi_number:04d}"
        else:
            return f"{specimen_id}.{block_id}.{section_id}.{substrate_media_id}.ROI{roi_number:03d}"

    @classmethod
    def parse_hierarchy_level(cls, roi_id: str) -> int:
        """Calculate hierarchy level from ROI ID."""
        return roi_id.count(".ROI")

    @property
    def is_parent(self) -> bool:
        """Check if this ROI has children (computed property)."""
        return False

    class Settings:
        name = "rois"
        indexes = [
            IndexModel(
                [("roi_id", ASCENDING)],
                name="roi_id_unique_index",
                unique=True,
            ),
            IndexModel([("section_id", ASCENDING)], name="section_id_index"),
            IndexModel([("block_id", ASCENDING)], name="block_id_index"),
            IndexModel([("specimen_id", ASCENDING)], name="specimen_id_index"),
            IndexModel([("substrate_media_id", ASCENDING)], name="substrate_media_id_index"),
            IndexModel([("hierarchy_level", ASCENDING)], name="hierarchy_level_index"),
            IndexModel([("updated_at", ASCENDING)], name="updated_at_index"),
            IndexModel([("section_ref.id", ASCENDING)], name="section_ref_index"),
            IndexModel(
                [("parent_roi_ref.id", ASCENDING)],
                name="parent_roi_ref_index",
                sparse=True,
            ),
            IndexModel([("barcode", ASCENDING)], name="barcode_index", sparse=True),
            IndexModel(
                [("section_id", ASCENDING), ("hierarchy_level", ASCENDING)],
                name="section_hierarchy_index",
            ),
            IndexModel(
                [
                    ("specimen_id", ASCENDING),
                    ("block_id", ASCENDING),
                    ("section_id", ASCENDING),
                    ("substrate_media_id", ASCENDING),
                ],
                name="hierarchy_path_index",
            ),
        ]
