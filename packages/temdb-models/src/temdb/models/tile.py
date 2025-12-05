from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .utils.uri import URI


class Matcher(BaseModel):
    model_config = ConfigDict(extra="allow")

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
    pX: list[float] = Field(..., description="X position of the points in the template tile")
    pY: list[float] = Field(..., description="Y position of the points in the template tile")
    qX: list[float] = Field(..., description="X position of the points in the reference tile")
    qY: list[float] = Field(..., description="Y position of the points in the reference tile")


class TileBase(BaseModel):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    stage_position: dict[str, float] | None = Field(
        None, description="Stage position of the tile in stage coordinates in nm"
    )
    raster_position: dict[str, int] | None = Field(None, description="Row, column raster position of the tile")
    focus_score: float | None = Field(None, description="Focus score of the tile")
    min_value: float | None = Field(None, description="Minimum pixel value of the tile")
    max_value: float | None = Field(None, description="Maximum pixel value of the tile")
    mean_value: float | None = Field(None, description="Mean pixel value of the tile")
    std_value: float | None = Field(None, description="Standard deviation of pixel values of the tile")
    image_path: URI | None = Field(None, description="URL to the image of the tile")
    matcher: list[Matcher] | None = Field(None, description="List of matchers for the tile")
    supertile_id: str | None = Field(None, description="ID of the supertile the tile belongs to")
    supertile_raster_position: dict[str, int] | None = Field(
        None, description="Row, column raster position of the supertile"
    )


class TileCreate(TileBase):
    tile_id: str = Field(..., description="Unique tile identifier")
    raster_index: int = Field(..., description="Index of the tile in the raster")
    stage_position: dict[str, float] = Field(..., description="Stage position of the tile in stage coordinates in nm")
    raster_position: dict[str, int] = Field(..., description="Row, column raster position of the tile")
    focus_score: float = Field(..., description="Focus score of the tile")
    min_value: float = Field(..., description="Minimum pixel value of the tile")
    max_value: float = Field(..., description="Maximum pixel value of the tile")
    mean_value: float = Field(..., description="Mean pixel value of the tile")
    std_value: float = Field(..., description="Standard deviation of pixel values of the tile")
    image_path: URI = Field(..., description="URL to the image of the tile")


class TileUpdate(TileBase):
    pass


class TileResponse(TileBase):
    tile_id: str = Field(..., description="Unique tile identifier")
    acquisition_id: str = Field(..., description="Parent acquisition ID")
    raster_index: int = Field(..., description="Index of the tile in the raster")
    stage_position: dict[str, float] = Field(..., description="Stage position of the tile in stage coordinates in nm")
    raster_position: dict[str, int] = Field(..., description="Row, column raster position of the tile")
    focus_score: float = Field(..., description="Focus score of the tile")
    min_value: float = Field(..., description="Minimum pixel value of the tile")
    max_value: float = Field(..., description="Maximum pixel value of the tile")
    mean_value: float = Field(..., description="Mean pixel value of the tile")
    std_value: float = Field(..., description="Standard deviation of pixel values of the tile")
    image_path: URI = Field(..., description="URL to the image of the tile")

    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int | None = Field(None, description="Document version number")
