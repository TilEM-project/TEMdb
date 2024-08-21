from typing import Dict, Optional
from pydantic import BaseModel
from beanie import Document, Link, PydanticObjectId
from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.enum_schemas import MediaType, SectionQuality


class SectionMetrics(BaseModel):
    sectioning_metadata: Optional[Dict]
    quality: Optional[SectionQuality]
    tissue_confidence_score: Optional[float]


class SectionCreate(BaseModel):
    section_id: str
    number: int
    optical_image: Optional[Dict] = None
    section_metrics: Optional[SectionMetrics]
    media_type: MediaType
    media_id: str
    relative_position: Optional[int] = None
    barcode: Optional[str] = None
    cut_session_id: PydanticObjectId


class SectionUpdate(BaseModel):
    number: Optional[int] = None
    optical_image: Optional[Dict] = None
    sectioning_metadata: Optional[Dict] = None
    quality: Optional[SectionQuality] = None
    tissue_confidence_score: Optional[float] = None
    relative_position: Optional[int] = None
    barcode: Optional[str] = None


class Section(Document):
    section_id: str
    number: int
    optical_image: Optional[Dict]
    section_metrics: Optional[SectionMetrics]
    media_type: MediaType
    media_id: str
    relative_position: Optional[int]
    barcode: Optional[str]
    cut_session: Link[CuttingSession]

    class Settings:
        name = "sections"
        indexes = [
            IndexModel(
                [("section_id", ASCENDING), ("cut_session.id", ASCENDING)],
                unique=True,
                name="section_cut_session_index",
            ),
            IndexModel(
                [("cut_session.id", ASCENDING), ("number", ASCENDING)],
                name="cut_session_number_index",
            ),
            IndexModel(
                [
                    ("media_type", ASCENDING),
                    ("media_id", ASCENDING),
                    ("relative_position", ASCENDING),
                ],
                name="media_position_index",
            ),
            IndexModel([("quality", ASCENDING)], name="quality_index"),
            IndexModel(
                [("tissue_confidence_score", DESCENDING)],
                name="tissue_confidence_score_index",
            ),
            IndexModel([("barcode", ASCENDING)], sparse=True, name="barcode_index"),
        ]
