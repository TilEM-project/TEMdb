from typing import List, Dict, Optional
from enum import Enum
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from temdb.models.v2.acquisition import Acquisition
from temdb.models.v2.tile import Tile

analysis_api = APIRouter(
    prefix="/analysis",
    tags=["Analysis"],
)


class TileStats(BaseModel):
    total_tiles: int
    average_focus_score: float
    min_focus_score: float
    max_focus_score: float
    average_intensity: float


class MatcherStats(BaseModel):
    average_match_quality: float
    min_match_quality: float
    max_match_quality: float


class Heatmaps(BaseModel):
    focus_scores: List[List[float]]
    std_dev: List[List[float]]
    matcher_row_quality: List[List[float]]
    matcher_col_quality: List[List[float]]
    raster_positions: List[Dict[str, int]]

class HeatmapType(str, Enum):
    FOCUS_SCORE = "focus_score"
    STD_DEV = "std_dev"
    MATCHER_ROW_QUALITY = "matcher_row_quality"
    MATCHER_COL_QUALITY = "matcher_col_quality"



@analysis_api.get("/{acquisition_id}/tile-stats", response_model=TileStats)
async def get_tile_stats(acquisition_id: str):
    raise NotImplementedError


@analysis_api.get("/{acquisition_id}/matcher-stats", response_model=MatcherStats)
async def get_matcher_stats(acquisition_id: str):
    raise NotImplementedError


@analysis_api.get("/{acquisition_id}/low-quality-tiles", response_model=List[Dict])
async def get_low_quality_tiles(acquisition_id: str):
    raise NotImplementedError


@analysis_api.get("/{acquisition_id}/heatmap", response_model=Heatmaps)
async def generate_tile_heatmaps(acquisition_id: str) -> Heatmaps:
    raise NotImplementedError


@analysis_api.get("/{acquisition_id}/heatmap/{heatmap_type}")
async def get_heatmap(acquisition_id: str, heatmap_type: HeatmapType):
    raise NotImplementedError
