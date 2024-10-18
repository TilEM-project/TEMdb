from typing import List, Dict, Optional
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


class HeatMapData(BaseModel):
    focus_scores: List[List[float]]
    std_dev: List[List[float]]
    matcher_row_quality: List[List[float]]
    matcher_col_quality: List[List[float]]
    raster_positions: List[Dict[str, int]]


@analysis_api.get("/tiles", response_model=List[Dict])
async def get_tiles():
    raise NotImplementedError


@analysis_api.get("/tile-stats", response_model=TileStats)
async def get_tile_stats(acquisition_id: str):
    raise NotImplementedError


@analysis_api.get("/matcher-stats", response_model=MatcherStats)
async def get_matcher_stats(acquisition_id: str):
    raise NotImplementedError


@analysis_api.get("/low-quality-tiles", response_model=List[Dict])
async def get_low_quality_tiles():
    raise NotImplementedError


@analysis_api.get("/extreme-intensity-tiles", response_model=List[Dict])
async def get_extreme_intensity_tiles(
    low_threshold: float = Query(10, ge=0),
    high_threshold: float = Query(245, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    raise NotImplementedError


@analysis_api.get("/acquisitions/{acquisition_id}/heatmap", response_model=HeatMapData)
async def get_acquisition_heatmap(acquisition_id: str) -> HeatMapData:
    raise NotImplementedError


@analysis_api.get("/acquisitions/{acquisition_id}/heatmap/{metric}")
async def get_acquisition_heatmap_metric(acquisition_id: str, metric: str):
    raise NotImplementedError
