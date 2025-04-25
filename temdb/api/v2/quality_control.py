import statistics
from enum import Enum
from typing import Dict, List
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from temdb.models.error import APIErrorResponse
from temdb.models.v2.acquisition import Acquisition
from temdb.models.v2.quality_control import (
    AcquisitionFocusScoresResponse,
    TileFocusScore,
)
from temdb.models.v2.tile import Tile

qc_api = APIRouter(
    prefix="/qc",
    tags=["Quality Control"],
)

logger = logging.getLogger(__name__)


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


@qc_api.get("/{acquisition_id}/tile-stats", response_model=TileStats)
async def get_tile_stats(acquisition_id: str):
    raise HTTPException(status_code=501, detail="Not Implemented")


@qc_api.get("/{acquisition_id}/matcher-stats", response_model=MatcherStats)
async def get_matcher_stats(acquisition_id: str):
    raise HTTPException(status_code=501, detail="Not Implemented")


@qc_api.get("/{acquisition_id}/low-quality-tiles", response_model=List[Dict])
async def get_low_quality_tiles(acquisition_id: str):
    raise HTTPException(status_code=501, detail="Not Implemented")


@qc_api.get("/{acquisition_id}/heatmap", response_model=Heatmaps)
async def generate_tile_heatmaps(acquisition_id: str) -> Heatmaps:
    raise HTTPException(status_code=501, detail="Not Implemented")


@qc_api.get("/{acquisition_id}/heatmap/{heatmap_type}")
async def get_heatmap(acquisition_id: str, heatmap_type: HeatmapType):
    raise HTTPException(status_code=501, detail="Not Implemented")


@qc_api.get(
    "/{acquisition_id}/focus-scores",
    response_model=AcquisitionFocusScoresResponse,
    summary="Get focus scores for all tiles in an acquisition",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": APIErrorResponse,
            "description": "Acquisition not found",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": APIErrorResponse,
            "description": "Internal server error",
        },
    },
)
async def get_acquisition_focus_scores(acquisition_id: str):
    """
    Retrieves the focus score for every tile associated with the
    specified `acquisition_id`. Includes summary statistics.
    """
    logger.info(f"Fetching focus scores for acquisition_id: {acquisition_id}")

    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        logger.warning(f"Acquisition not found: {acquisition_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Acquisition with id '{acquisition_id}' not found.",
        )

    tile_cursor = Tile.find(
        Tile.acquisition_id == acquisition_id,
        projection_model=TileFocusScore,
    ).sort(Tile.raster_index)

    tiles_data = await tile_cursor.to_list()

    if not tiles_data:
        logger.info(f"No tiles found for acquisition {acquisition_id}")
        return AcquisitionFocusScoresResponse(
            acquisition_id=acquisition_id,
            tile_count=0,
            focus_scores=[],
            mean_focus=None,
            median_focus=None,
            stddev_focus=None,
            min_focus=None,
            max_focus=None,
        )

    scores = [tile.focus_score for tile in tiles_data if tile.focus_score is not None]

    mean_focus = None
    median_focus = None
    stddev_focus = None
    min_focus = None
    max_focus = None

    if scores:
        try:
            mean_focus = statistics.mean(scores)
            median_focus = statistics.median(scores)
            min_focus = min(scores)
            max_focus = max(scores)
            if len(scores) > 1:
                stddev_focus = statistics.stdev(scores)
            else:
                stddev_focus = 0.0
        except statistics.StatisticsError as e:
            logger.warning(
                f"Could not calculate statistics for acquisition {acquisition_id}: {e}"
            )
        except Exception as e:
            logger.error(
                f"Unexpected error calculating statistics for {acquisition_id}: {e}"
            )

    response = AcquisitionFocusScoresResponse(
        acquisition_id=acquisition_id,
        tile_count=len(tiles_data),
        focus_scores=tiles_data,
        mean_focus=mean_focus,
        median_focus=median_focus,
        stddev_focus=stddev_focus,
        min_focus=min_focus,
        max_focus=max_focus,
    )

    logger.info(
        f"Returning {len(tiles_data)} focus scores for acquisition {acquisition_id}"
    )
    return response
