from typing import List, Dict, Optional
from beanie import PydanticObjectId
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from temdb.models.v2.acquisition import Acquisition

analysis_api = APIRouter(
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


@analysis_api.get("/tiles", response_model=List[Dict])
async def get_tiles(
    min_focus_score: float = Query(None, ge=0, le=1),
    max_focus_score: float = Query(None, ge=0, le=1),
    min_intensity: float = Query(None, ge=0),
    max_intensity: float = Query(None, ge=0),
    acquisition_id: Optional[PydanticObjectId] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    query = {}
    if min_focus_score is not None:
        query["tiles.focus_score"] = {"$gte": min_focus_score}
    if max_focus_score is not None:
        query.setdefault("tiles.focus_score", {})["$lte"] = max_focus_score
    if min_intensity is not None:
        query["tiles.mean_value"] = {"$gte": min_intensity}
    if max_intensity is not None:
        query.setdefault("tiles.mean_value", {})["$lte"] = max_intensity
    if acquisition_id:
        query["_id"] = acquisition_id

    pipeline = [
        {"$match": query},
        {"$unwind": "$tiles"},
        {"$match": query},
        {"$skip": skip},
        {"$limit": limit},
        {
            "$project": {
                "acquisition_id": "$_id",
                "tile_id": "$tiles.tile_id",
                "focus_score": "$tiles.focus_score",
                "mean_intensity": "$tiles.mean_value",
                "raster_position": "$tiles.raster_position",
                "stage_position": "$tiles.stage_position",
            }
        },
    ]

    return await Acquisition.aggregate(pipeline).to_list()


@analysis_api.get("/tile-stats", response_model=TileStats)
async def get_tile_stats(acquisition_id: Optional[PydanticObjectId] = None):
    match_stage = {} if acquisition_id is None else {"$match": {"_id": acquisition_id}}

    pipeline = [
        match_stage,
        {"$unwind": "$tiles"},
        {
            "$group": {
                "_id": None,
                "total_tiles": {"$sum": 1},
                "average_focus_score": {"$avg": "$tiles.focus_score"},
                "min_focus_score": {"$min": "$tiles.focus_score"},
                "max_focus_score": {"$max": "$tiles.focus_score"},
                "average_intensity": {"$avg": "$tiles.mean_value"},
            }
        },
    ]

    result = await Acquisition.aggregate(pipeline).to_list()
    if not result:
        raise HTTPException(status_code=404, detail="No tiles found")

    stats = result[0]
    return TileStats(**stats)


@analysis_api.get("/matcher-stats", response_model=MatcherStats)
async def get_matcher_stats(acquisition_id: Optional[PydanticObjectId] = None):
    match_stage = {} if acquisition_id is None else {"$match": {"_id": acquisition_id}}

    pipeline = [
        match_stage,
        {"$unwind": "$tiles"},
        {"$unwind": "$tiles.matcher"},
        {
            "$group": {
                "_id": None,
                "average_match_quality": {"$avg": "$tiles.matcher.match_quality"},
                "min_match_quality": {"$min": "$tiles.matcher.match_quality"},
                "max_match_quality": {"$max": "$tiles.matcher.match_quality"},
            }
        },
    ]

    result = await Acquisition.aggregate(pipeline).to_list()
    if not result:
        raise HTTPException(status_code=404, detail="No matcher data found")

    stats = result[0]
    return MatcherStats(**stats)


@analysis_api.get("/low-quality-tiles", response_model=List[Dict])
async def get_low_quality_tiles(
    focus_score_threshold: float = Query(0.5, ge=0, le=1),
    limit: int = Query(10, ge=1, le=100),
):
    pipeline = [
        {"$unwind": "$tiles"},
        {"$match": {"tiles.focus_score": {"$lt": focus_score_threshold}}},
        {"$sort": {"tiles.focus_score": 1}},
        {"$limit": limit},
        {
            "$project": {
                "acquisition_id": "$_id",
                "tile_id": "$tiles.tile_id",
                "focus_score": "$tiles.focus_score",
                "mean_intensity": "$tiles.mean_value",
                "raster_position": "$tiles.raster_position",
            }
        },
    ]

    return await Acquisition.aggregate(pipeline).to_list()


@analysis_api.get("/extreme-intensity-tiles", response_model=List[Dict])
async def get_extreme_intensity_tiles(
    low_threshold: float = Query(10, ge=0),
    high_threshold: float = Query(245, ge=0),
    limit: int = Query(10, ge=1, le=100),
):
    pipeline = [
        {"$unwind": "$tiles"},
        {
            "$match": {
                "$or": [
                    {"tiles.min_value": {"$lt": low_threshold}},
                    {"tiles.max_value": {"$gt": high_threshold}},
                ]
            }
        },
        {"$limit": limit},
        {
            "$project": {
                "acquisition_id": "$_id",
                "tile_id": "$tiles.tile_id",
                "min_intensity": "$tiles.min_value",
                "max_intensity": "$tiles.max_value",
                "mean_intensity": "$tiles.mean_value",
                "raster_position": "$tiles.raster_position",
            }
        },
    ]

    return await Acquisition.aggregate(pipeline).to_list()


class HeatMapData(BaseModel):
    focus_scores: List[List[float]]
    std_dev: List[List[float]]
    matcher_row_quality: List[List[float]]
    matcher_col_quality: List[List[float]]
    raster_positions: List[Dict[str, int]]


@analysis_api.get("/acquisitions/{acquisition_id}/heatmap", response_model=HeatMapData)
async def get_acquisition_heatmap(acquisition_id: PydanticObjectId):
    acquisition = await Acquisition.get(acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    # Initialize data structures
    focus_scores = []
    std_dev = []
    matcher_row_quality = []
    matcher_col_quality = []
    raster_positions = []

    # Get the dimensions of the tile grid
    max_row = max(tile.raster_position["y"] for tile in acquisition.tiles.values())
    max_col = max(tile.raster_position["x"] for tile in acquisition.tiles.values())

    # Initialize 2D lists with None values
    focus_scores = [[None for _ in range(max_col + 1)] for _ in range(max_row + 1)]
    std_dev = [[None for _ in range(max_col + 1)] for _ in range(max_row + 1)]
    matcher_row_quality = [
        [None for _ in range(max_col + 1)] for _ in range(max_row + 1)
    ]
    matcher_col_quality = [
        [None for _ in range(max_col + 1)] for _ in range(max_row + 1)
    ]

    for tile_id, tile in acquisition.tiles.items():
        row = tile.raster_position["y"]
        col = tile.raster_position["x"]

        focus_scores[row][col] = tile.focus_score
        std_dev[row][col] = tile.std_value

        # Assuming the first matcher in the list corresponds to row and the second to column
        if len(tile.matcher) >= 2:
            matcher_row_quality[row][col] = tile.matcher[0].match_quality
            matcher_col_quality[row][col] = tile.matcher[1].match_quality

        raster_positions.append(tile.raster_position)

    return HeatMapData(
        focus_scores=focus_scores,
        std_dev=std_dev,
        matcher_row_quality=matcher_row_quality,
        matcher_col_quality=matcher_col_quality,
        raster_positions=raster_positions,
    )


@analysis_api.get("/acquisitions/{acquisition_id}/heatmap/{metric}")
async def get_acquisition_heatmap_metric(acquisition_id: PydanticObjectId, metric: str):
    heatmap_data = await get_acquisition_heatmap(acquisition_id)

    if metric == "focus_scores":
        return {
            "data": heatmap_data.focus_scores,
            "raster_positions": heatmap_data.raster_positions,
        }
    elif metric == "std_dev":
        return {
            "data": heatmap_data.std_dev,
            "raster_positions": heatmap_data.raster_positions,
        }
    elif metric == "matcher_row_quality":
        return {
            "data": heatmap_data.matcher_row_quality,
            "raster_positions": heatmap_data.raster_positions,
        }
    elif metric == "matcher_col_quality":
        return {
            "data": heatmap_data.matcher_col_quality,
            "raster_positions": heatmap_data.raster_positions,
        }
    else:
        raise HTTPException(status_code=400, detail="Invalid metric specified")
