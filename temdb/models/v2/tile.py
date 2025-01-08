from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from beanie import Document, Link

from pymongo import IndexModel, ASCENDING

from temdb.models.v2.acquisition import Acquisition


class Matcher(BaseModel):
    row: int = Field(..., description="Row index of the tile")
    col: int = Field(..., description="Column index of the tile")
    dX: float = Field(..., description="X offset of the tile")
    dY: float = Field(..., description="Y offset of the tile")
    dXsd: float = Field(..., description="X offset standard deviation of the tile")
    dYsd: float = Field(..., description="Y offset standard deviation of the tile")
    distance: float = Field(..., description="Distance between the tiles")
    rotation: float = Field(..., description="Rotation of the tile")
    match_quality: float = Field(..., description="Quality of the match")
    position: int = Field(..., description="Position of the match")
    pX: List[float] = Field(..., description="X position of the points in the template tile")
    pY: List[float] = Field(..., description="Y position of the points in the template tile")
    qX: List[float] = Field(
        ..., description="X position of the points in the reference tile"
    )
    qY: List[float] = Field(
        ..., description="Y position of the points in the reference tile"
    )


class TileCreate(BaseModel):
    tile_id: str = Field(..., description="ID of the tile")
    raster_index: int = Field(..., description="Index of the tile in the raster")
    stage_position: Dict[str, float] = Field(
        ..., description="Stage position of the tile in stage coordinates in nm"
    )
    raster_position: Dict[str, int] = Field(
        ..., description="Row, column raster position of the tile"
    )
    focus_score: float = Field(..., description="Focus score of the tile")
    min_value: float = Field(..., description="Minimum pixel value of the tile")
    max_value: float = Field(..., description="Maximum pixel value of the tile")
    mean_value: float = Field(..., description="Mean pixel value of the tile")
    std_value: float = Field(
        ..., description="Standard deviation of pixel values of the tile"
    )
    image_path: str = Field(..., description="URL to the image of the tile")
    matcher: Optional[List[Matcher]] = Field(
        None, description="List of matchers for the tile"
    )
    supertile_id: Optional[str] = Field(
        None, description="ID of the supertile the tile belongs to"
    )
    supertile_raster_position: Optional[Dict[str, int]] = Field(
        None, description="Row, column raster position of the supertile"
    )


class Tile(Document):
    tile_id: str = Field(..., description="ID of the tile")
    acquisition_id: str = Field(..., description="ID of the acquisition")
    raster_index: int = Field(..., description="Index of the tile in the raster")
    stage_position: Dict[str, float] = Field(..., description="Stage position of the tile in stage coordinates in nm")
    raster_position: Dict[str, int] = Field(..., description="Row, column raster position of the tile")
    focus_score: float = Field(..., description="Focus score of the tile")
    min_value: float = Field(..., description="Minimum pixel value of the tile")
    max_value: float = Field(..., description="Maximum pixel value of the tile")
    mean_value: float = Field(..., description="Mean pixel value of the tile")
    std_value: float = Field(..., description="Standard deviation of pixel values of the tile")
    image_path: str = Field(..., description="URL to the image of the tile")
    matcher: Optional[List[Matcher]] = Field(None, description="Matching data for the tile")
    supertile_id: Optional[str] = Field(None, description="ID of the supertile the tile belongs to")
    supertile_raster_position: Optional[Dict[str, int]] = Field(None, description="Row, column raster position of the supertile")

    class Settings:
        name = "tiles"
        indexes = [
            IndexModel([("tile_id", ASCENDING)], unique=True, name="tile_id_index"),
            IndexModel(
                [("acquisition_id", ASCENDING)], name="acquisition_id_index"
            ),  # do we need this?
            IndexModel([("supertile_id", ASCENDING)], name="supertile_id_index"),
        ]
