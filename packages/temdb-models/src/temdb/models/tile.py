from datetime import datetime

from pydantic import ConfigDict, Field

from .base import TEMDBModel
from .enums import MatchPosition
from .file_storage import FileObject


class StagePosition(TEMDBModel):
    x: float = Field(..., description="X axis stage position in nm")
    y: float = Field(..., description="Y axis stage position in nm")
    z: float | None = Field(None, description="Z axis stage position in nm")


class RasterPosition(TEMDBModel):
    row: int = Field(..., description="Raster scan row index")
    col: int = Field(..., description="Raster scan column index")


class Matcher(TEMDBModel):
    row: int = Field(..., description="Row index of the tile")
    col: int = Field(..., description="Column index of the tile")
    dX: float = Field(..., description="X offset of the tile")
    dY: float = Field(..., description="Y offset of the tile")
    dXsd: float = Field(..., description="X offset standard deviation of the tile")
    dYsd: float = Field(..., description="Y offset standard deviation of the tile")
    distance: float = Field(..., description="Distance between the tiles")
    rotation: float = Field(..., description="Rotation of the tile")
    match_quality: float = Field(..., description="Quality of the match")
    position: MatchPosition = Field(..., description="Position of the match")
    pX: list[float] = Field(..., description="X position of the points in the template tile")
    pY: list[float] = Field(..., description="Y position of the points in the template tile")
    qX: list[float] = Field(..., description="X position of the points in the reference tile")
    qY: list[float] = Field(..., description="Y position of the points in the reference tile")


class TileBase(TEMDBModel):
    stage_position: StagePosition | None = Field(
        None, description="Stage position of the tile in stage coordinates in nm"
    )
    focus_score: float | None = Field(None, description="Focus score of the tile")
    min_value: float | None = Field(None, description="Minimum pixel value of the tile")
    max_value: float | None = Field(None, description="Maximum pixel value of the tile")
    mean_value: float | None = Field(None, description="Mean pixel value of the tile")
    std_value: float | None = Field(None, description="Standard deviation of pixel values of the tile")
    image: FileObject | None = Field(None, description="The tile image")
    matcher: list[Matcher] | None = Field(None, description="List of matchers for the tile")
    supertile_id: str | None = Field(None, description="ID of the supertile the tile belongs to")
    supertile_raster_position: RasterPosition | None = Field(
        None, description="Row, column raster position of the supertile"
    )


class TileCreate(TileBase):
    raster_index: int = Field(..., description="Index of the tile in the raster")
    stage_position: StagePosition = Field(..., description="Stage position of the tile in stage coordinates in nm")
    raster_position: RasterPosition = Field(..., description="Row, column raster position of the tile")
    retake: int = Field(0, ge=0, le=32767, description="Capture number at this position within the run; 0 is the first")


class TileUpdate(TileBase):
    stage_position: StagePosition = Field(None, description="Stage position of the tile in stage coordinates in nm")


class TileResponse(TileBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    tile_id: str = Field(..., description="{montage_id}_r{row:03d}_c{col:03d}, plus _a{retake} for a retake")
    acquisition_id: str = Field(..., description="Parent acquisition ID")
    raster_index: int = Field(..., description="Index of the tile in the raster")
    stage_position: StagePosition = Field(..., description="Stage position of the tile in stage coordinates in nm")
    raster_position: RasterPosition = Field(..., description="Row, column raster position of the tile")
    retake: int = Field(..., description="Capture number at this position within the run; 0 is the first")

    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int | None = Field(None, description="Document version number")


class TileBulkDeleteResult(TEMDBModel):
    requested: int = Field(..., description="Distinct tile_ids in the request")
    deleted: int = Field(..., description="Tiles deleted")
    not_found: list[str] = Field(..., description="Requested tile_ids not found in this acquisition")


class TileDeleteAllResult(TEMDBModel):
    deleted: int = Field(..., description="Tiles deleted")
