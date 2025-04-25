from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TileFocusScore(BaseModel):
    """Represents focus score data for a single tile."""

    tile_id: str = Field(..., description="Unique ID of the tile.")
    raster_index: int = Field(
        ..., description="Sequential index of the tile within the acquisition raster."
    )
    focus_score: float = Field(..., description="Calculated focus score for the tile.")


class AcquisitionFocusScoresResponse(BaseModel):
    """Response model containing focus scores for an acquisition."""

    acquisition_id: str = Field(..., description="ID of the acquisition analyzed.")
    tile_count: int = Field(
        ..., description="Total number of tiles found for this acquisition."
    )
    focus_scores: List[TileFocusScore] = Field(
        ..., description="List of focus scores for each tile."
    )
    mean_focus: Optional[float] = Field(
        None, description="Mean focus score across all tiles."
    )
    median_focus: Optional[float] = Field(
        None, description="Median focus score across all tiles."
    )
    stddev_focus: Optional[float] = Field(
        None, description="Standard deviation of focus scores across all tiles."
    )
    min_focus: Optional[float] = Field(None, description="Minimum focus score found.")
    max_focus: Optional[float] = Field(None, description="Maximum focus score found.")


class BadFocusTileInfo(BaseModel):
    tile_id: str
    acquisition_id: str
    raster_index: int
    focus_score: float
    image_path: str
    stage_position: Dict[str, float]
    roi_id: Optional[int] = None
    specimen_id: Optional[str] = None


class BadFocusTilesResponse(BaseModel):
    threshold: float
    count: int
    tiles: List[BadFocusTileInfo]
