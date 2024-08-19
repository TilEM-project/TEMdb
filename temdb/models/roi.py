from typing import Dict, Optional
from pydantic import BaseModel
from beanie import Document, Link, PydanticObjectId
from pymongo import IndexModel, ASCENDING

from temdb.models.section import Section


class ROICreate(BaseModel):
    roi_id: str
    name: str
    aperture_centroid: Dict
    brightfield_center: Dict
    barcode: Optional[int] = None
    parameters: Dict
    is_lens_correction_roi: bool = False
    section_id: PydanticObjectId
    parent_roi_id: Optional[PydanticObjectId] = None


class ROIUpdate(BaseModel):
    name: Optional[str] = None
    aperture_centroid: Optional[Dict] = None
    brightfield_center: Optional[Dict] = None
    barcode: Optional[int] = None
    parameters: Optional[Dict] = None
    is_lens_correction_roi: Optional[bool] = None
    thumbnail: str = None


class ROI(Document):
    roi_id: str
    name: str
    aperture_centroid: Dict
    brightfield_center: Dict
    barcode: Optional[int]
    parent_roi: Optional[Link["ROI"]]
    parameters: Dict
    is_lens_correction_roi: bool = False
    section: Link[Section]
    thumbnail: Optional[str] = None

    class Settings:
        name = "rois"
        indexes = [
            IndexModel([("roi_id", ASCENDING)], unique=True, name="roi_id_index"),
            IndexModel(
                [("section.id", ASCENDING), ("name", ASCENDING)],
                name="section_name_index",
            ),
            IndexModel([("parent_roi.id", ASCENDING)], name="parent_roi_index"),
            IndexModel(
                [("is_lens_correction_roi", ASCENDING)], name="lens_correction_index"
            ),
        ]
