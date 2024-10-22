from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from beanie import Document, Link

from pymongo import IndexModel, ASCENDING

from temdb.models.v2.acquisition import Acquisition


class Matcher(BaseModel):
    row: int
    col: int
    dX: float
    dY: float
    dXsd: float
    dYsd: float
    distance: float
    rotation: float
    match_quality: float
    position: int
    pX: List[float] = Field(...)
    pY: List[float] = Field(...)
    qX: List[float] = Field(...)
    qY: List[float] = Field(...)


class TileCreate(BaseModel):
    tile_id: str
    raster_index: int
    stage_position: Dict[str, float]
    raster_position: Dict[str, int]
    focus_score: float
    min_value: float
    max_value: float
    mean_value: float
    std_value: float
    image_path: str
    matcher: Optional[List[Matcher]]
    supertile_id: Optional[str] = None
    supertile_raster_position: Optional[Dict[str, int]] = None


class Tile(Document):
    tile_id: str
    acquisition_id: str
    raster_index: int
    stage_position: Dict[str, float]
    raster_position: Dict[str, int]
    focus_score: float
    min_value: float
    max_value: float
    mean_value: float
    std_value: float
    image_path: str
    matcher: List[Matcher]
    supertile_id: Optional[str] = None
    supertile_raster_position: Optional[Dict[str, int]] = None

    class Settings:
        name = "tiles"
        indexes = [
            IndexModel([("tile_id", ASCENDING)], unique=True, name="tile_id_index"),
            IndexModel([("acquisition_id", ASCENDING)], name="acquisition_id_index"), # do we need this?
            IndexModel([("supertile_id", ASCENDING)], name="supertile_id_index"),
        ]
