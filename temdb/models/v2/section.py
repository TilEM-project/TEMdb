from typing import Dict, Optional
from pydantic import BaseModel, Field
from beanie import Document, Link
from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.enum_schemas import MediaType, SectionQuality


class SectionMetrics(BaseModel):
    sectioning_metadata: Optional[Dict] = Field(None, description="Field for storing arbitrary metadata")
    quality: Optional[SectionQuality] = Field(None, description="State of the health of a section") 
    tissue_confidence_score: Optional[float] = Field(None, description="Confidence score for tissue detection on substrate")

class SectionBase(BaseModel):
    section_number: Optional[int] = Field(None, description="Number of section from collection")
    optical_image: Optional[Dict] = Field(None, description="Optical image of section collected before imaging")
    section_metrics: Optional[SectionMetrics] = Field(None, description="Metrics of section")
    relative_position: Optional[int] = Field(None, description="Position of section relative to substrate centroid")
    barcode: Optional[str] = Field(None, description="Barcode of section if using a barcode system per substrate aperture")

class SectionCreate(SectionBase):
    section_id: str = Field(..., description="ID of section")
    media_type: MediaType = Field(..., description="Type of substrate the section is on")
    media_id: str = Field(..., description="ID of substrate the section is on")
    cutting_session_id: str = Field(..., description="ID of cutting session section was collected in")
    section_number: int  = Field(..., description="Number of section from collection")

class SectionUpdate(SectionBase):
    quality: Optional[SectionQuality] = Field(None, description="State of the health of a section")
    tissue_confidence_score: Optional[float] = Field(None, description="Confidence score for tissue detection on substrate")

class Section(Document):
    section_id: str = Field(..., description="ID of section")
    section_number: int = Field(..., description="Number of section from collection")
    optical_image: Optional[Dict] = Field(None, description="Optical image of section collected before imaging")
    section_metrics: Optional[SectionMetrics] = Field(None, description="Metrics of section")
    media_type: MediaType = Field(..., description="Type of substrate the section is on")
    media_id: str = Field(..., description="ID of substrate the section is on")
    relative_position: Optional[int] = Field(None, description="Position of section relative to substrate centroid")
    barcode: Optional[str] = Field(None, description="Barcode of section if using a barcode system per substrate aperture")
    cutting_session_id: Link[CuttingSession] =  Field(..., description="ID of cutting session section was collected in")

    class Settings:
        name = "sections"
        indexes = [
            IndexModel(
                [("section_id", ASCENDING), ("cut_session.id", ASCENDING)],
                unique=True,
                name="section_cut_session_index",
            ),
            IndexModel(
                [("cutting_session_id.id", ASCENDING), ("number", ASCENDING)],
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
