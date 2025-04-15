from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import logging
from fastapi import APIRouter, Body, HTTPException, Query, Response

from temdb.models.v2.acquisition import (
    Acquisition,
    AcquisitionCreate,
    AcquisitionUpdate,
    StorageLocation,
    StorageLocationCreate,
)
from temdb.models.v2.task import AcquisitionTask
from temdb.models.v2.roi import ROI
from temdb.models.v2.tile import Tile, TileCreate
from fastapi import BackgroundTasks, status, Depends
import math
from temdb.config import get_config, BaseConfig

acquisition_api = APIRouter(
    tags=["Acquisitions"],
)


@acquisition_api.get(
    "/acquisitions",
    response_model=Dict[str, Any],
    responses={
        200: {"description": "List of acquisitions"},
        400: {"description": "Invalid parameters"},
        500: {"description": "Internal server error"},
    },
)
async def list_acquisitions(
    response: Response,
    cursor: Optional[str] = Query(None, description="Cursor for pagination"),
    limit: int = Query(50, ge=1, le=1000, description="Number of records to return"),
    sort_by: str = Query("start_time", description="Field to sort by"),
    sort_order: int = Query(-1, ge=-1, le=1, description="Sort order (-1=desc, 1=asc)"),
    montage_set_name: Optional[str] = Query(
        None, description="Filter by montage set name"
    ),
    magnification: Optional[int] = Query(
        None, ge=1, description="Filter by magnification"
    ),
    status: Optional[str] = Query(None, description="Filter by acquisition status"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    fields: List[str] = Query(
        ["acquisition_id", "status", "start_time", "montage_set_name"],
        description="Fields to return",
    ),
) -> Dict[str, Any]:
    try:

        query = {}
        if montage_set_name:
            query["montage_set_name"] = montage_set_name
        if magnification is not None:
            query["acquisition_settings.magnification"] = magnification
        if status:
            query["status"] = status
        if start_date:
            query["start_time"] = {"$gte": start_date}
        if end_date:
            query["start_time"] = {"$lte": end_date}
        if cursor:
            query["_id"] = {"$gt": cursor}

        projection = {field: 1 for field in fields}
        projection["_id"] = 1

        pipeline = [
            {"$match": query},
            {"$project": projection},
            {"$sort": {sort_by: sort_order}},
            {"$limit": limit + 1},
        ]

        acquisitions = await Acquisition.aggregate(pipeline).to_list()

        has_more = len(acquisitions) > limit
        if has_more:
            acquisitions = acquisitions[:-1]

        total_count = await Acquisition.find(query).count()

        next_cursor = (
            str(acquisitions[-1]["_id"]) if acquisitions and has_more else None
        )

        response.headers["Cache-Control"] = "private, max-age=300"
        response.headers["X-Total-Count"] = str(total_count)

        return {
            "acquisitions": acquisitions,
            "metadata": {
                "total_count": total_count,
                "returned_count": len(acquisitions),
                "has_more": has_more,
                "next_cursor": next_cursor,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving acquisitions: {str(e)}"
        )


@acquisition_api.post("/acquisitions", response_model=Acquisition)
async def create_acquisition(acquisition: AcquisitionCreate) -> Acquisition:
    """Create a new acquisition

    Args:
        acquisition (AcquisitionCreate): Acquisition data

    Raises:
        HTTPException: 404 if ROI or imaging session not found

    Returns:
        Acquisition
    """
    roi = await ROI.find_one(ROI.roi_id == acquisition.roi_id)
    if not roi:
        raise HTTPException(status_code=404, detail="ROI not found")

    acquisition_task_id = await AcquisitionTask.find_one(
        AcquisitionTask.task_id == acquisition.acquisition_task_id
    )
    if not acquisition_task_id:
        raise HTTPException(status_code=404, detail="Acquisition task not found")

    new_acquisition = Acquisition(
        montage_id=acquisition.montage_id,
        specimen_id=acquisition_task_id.specimen_id,
        acquisition_id=acquisition.acquisition_id,
        roi_id=roi.id,
        acquisition_task_id=acquisition_task_id.id,
        hardware_settings=acquisition.hardware_settings,
        acquisition_settings=acquisition.acquisition_settings,
        calibration_info=acquisition.calibration_info,
        status=acquisition.status,
        tilt_angle=acquisition.tilt_angle,
        lens_correction=acquisition.lens_correction,
        start_time=acquisition.start_time or datetime.now(timezone.utc),
        montage_set_name=acquisition.montage_set_name,
        sub_region=acquisition.sub_region,
        replaces_acquisition_id=acquisition.replaces_acquisition_id,
    )
    await new_acquisition.insert()
    return new_acquisition


@acquisition_api.get("/acquisitions/{acquisition_id}", response_model=Acquisition)
async def get_acquisition(acquisition_id: str):
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")
    return acquisition


@acquisition_api.patch("/acquisitions/{acquisition_id}", response_model=Acquisition)
async def update_acquisition(
    acquisition_id: str, updated_fields: AcquisitionUpdate = Body(...)
):
    existing_acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not existing_acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    update_data = updated_fields.model_dump(exclude_unset=True)

    if update_data:
        for field, value in update_data.items():
            setattr(existing_acquisition, field, value)

        await existing_acquisition.save()

    return existing_acquisition


@acquisition_api.delete("/acquisitions/{acquisition_id}", response_model=dict)
async def delete_acquisition(acquisition_id: str):
    acquisition = await Acquisition.find_one(Acquisition.acquisition_id == acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    await acquisition.delete()
    return {"message": "Acquisition deleted successfully"}

@acquisition_api.post("/acquisitions/{acquisition_id}/tiles", response_model=Tile)
async def add_tile_to_acquisition(acquisition_id: str, tile: TileCreate):
    acquisition = await Acquisition.find_one(Acquisition.acquisition_id == acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    new_tile = Tile(
        tile_id=tile.tile_id,
        acquisition_id=acquisition.id,
        raster_index=tile.raster_index,
        stage_position=tile.stage_position,
        raster_position=tile.raster_position,
        focus_score=tile.focus_score,
        min_value=tile.min_value,
        max_value=tile.max_value,
        mean_value=tile.mean_value,
        std_value=tile.std_value,
        image_path=tile.image_path,
        matcher=tile.matcher,
        supertile_id=tile.supertile_id,
        supertile_raster_position=tile.supertile_raster_position,
    )
    await new_tile.insert()

    return new_tile


async def process_tile_batch(tiles: List[TileCreate], acquisition_id: str):
    """Background task to process a batch of tiles"""
    try:
        new_tiles = [
            Tile(
                tile_id=tile.tile_id,
                acquisition_id=acquisition_id,
                raster_index=tile.raster_index,
                stage_position=tile.stage_position,
                raster_position=tile.raster_position,
                focus_score=tile.focus_score,
                min_value=tile.min_value,
                max_value=tile.max_value,
                mean_value=tile.mean_value,
                std_value=tile.std_value,
                image_path=tile.image_path,
                matcher=tile.matcher,
                supertile_id=tile.supertile_id,
                supertile_raster_position=tile.supertile_raster_position,
            )
            for tile in tiles
        ]
        await Tile.insert_many(new_tiles)

    except Exception as e:
        logging.error(f"Error processing tile batch: {str(e)}")


@acquisition_api.post("/acquisitions/{acquisition_id}/tiles/bulk", response_model=dict)
async def add_tiles_to_acquisition(
    acquisition_id: str,
    tiles: List[TileCreate],
    background_tasks: BackgroundTasks,
    config: BaseConfig = Depends(get_config),
):
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Acquisition not found"
        )

    total_tiles = len(tiles)

    if total_tiles <= config.max_batch_size:
        try:
            result = await process_tile_batch(tiles, acquisition_id)

            return {
                "success": True,
                "inserted_count": len(result),
                "acquisition_id": acquisition_id,
                "processing_mode": "direct",
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error inserting tiles: {str(e)}"
            )
    else:
        num_batches = math.ceil(total_tiles / config.max_batch_size)

        for i in range(num_batches):
            start_idx = i * config.max_batch_size
            end_idx = start_idx + config.max_batch_size
            batch = tiles[start_idx:end_idx]
            background_tasks.add_task(process_tile_batch, batch, acquisition_id)

        return {
            "success": True,
            "total_tiles": total_tiles,
            "num_batches": num_batches,
            "acquisition_id": acquisition_id,
            "processing_mode": "background",
            "message": f"Processing {total_tiles} tiles in {num_batches} batches",
        }


# @acquisition_api.post("/acquisitions/{acquisition_id}/tiles/bulk", response_model=dict)
# async def add_tiles_to_acquisition(acquisition_id: str, tiles: List[TileCreate]):
#     new_tiles = [
#         Tile(
#             tile_id=tile.tile_id,
#             acquisition_id=acquisition_id,
#             raster_index=tile.raster_index,
#             stage_position=tile.stage_position,
#             raster_position=tile.raster_position,
#             focus_score=tile.focus_score,
#             min_value=tile.min_value,
#             max_value=tile.max_value,
#             mean_value=tile.mean_value,
#             std_value=tile.std_value,
#             image_path=tile.image_path,
#             matcher=tile.matcher,
#             supertile_id=tile.supertile_id,
#             supertile_raster_position=tile.supertile_raster_position,
#         )
#         for tile in tiles
#     ]
#     try:
#         result = await Tile.insert_many(new_tiles)

#         return {
#             "success": True,
#             "inserted_count": len(result),
#             "acquisition_id": acquisition_id,
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error inserting tiles: {str(e)}")


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/tiles/{tile_id}", response_model=Tile
)
async def get_tile_from_acquisition(acquisition_id: str, tile_id: str):
    acquisition = await Acquisition.find_one(Acquisition.acquisition_id == acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")
    
    tile_data = await Tile.find_one(
        Tile.tile_id == tile_id,
        Tile.acquisition_id == acquisition.id
    )
    
    if not tile_data:
        raise HTTPException(status_code=404, detail="Tile not found")
    
    return tile_data


@acquisition_api.get("/acquisitions/{acquisition_id}/tiles", response_model=List[Dict])
async def get_tiles_from_acquisition(
    response: Response,
    acquisition_id: str,
    cursor: Optional[int] = Query(None, description="Last raster_index seen"),
    limit: int = Query(100, ge=1, le=1000),
    fields: List[str] = Query(
        ["tile_id", "raster_index", "stage_position", "raster_position"],
        description="Fields to return",
    ),
):
    projection = {field: 1 for field in fields}
    projection["_id"] = 0

    query = {"acquisition_id": acquisition_id}
    if cursor:
        query["raster_index"] = {"$gt": cursor}

    pipeline = [
        {"$match": query},
        {"$project": projection},
        {"$sort": {"raster_index": 1}},
        {"$limit": limit + 1},
    ]

    tiles = await Tile.aggregate(pipeline).to_list()

    has_more = len(tiles) > limit
    if has_more:
        tiles = tiles[:-1]

    next_cursor = tiles[-1]["raster_index"] if tiles else None

    response.headers["Cache-Control"] = "private, max-age=300"  # 5 min cache

    return {
        "tiles": tiles,
        "next_cursor": next_cursor,
        "has_more": has_more,
        "total_count": await Tile.find(query).count(),
    }


@acquisition_api.post(
    "/acquisitions/{acquisition_id}/storage-locations", response_model=Acquisition
)
async def add_storage_location(
    acquisition_id: str, storage_location: StorageLocationCreate
):
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    new_location = StorageLocation(**storage_location.model_dump())
    acquisition.storage_locations.append(new_location)
    await acquisition.save()
    return acquisition


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/current-storage",
    response_model=Optional[StorageLocation],
)
async def get_current_storage_location(acquisition_id: str):
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    return acquisition.get_current_storage_location()


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/minimap-uri",
    response_model=Dict[str, Optional[str]],
)
async def get_minimap_uri(acquisition_id: str):
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    return {"minimap_uri": acquisition.get_minimap_uri()}


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/tile-count", response_model=Dict[str, int]
)
async def get_tile_count(acquisition_id: str):
    tile_count = await Tile.find(Tile.acquisition_id == acquisition_id).count()
    return {"tile_count": tile_count}


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/tiles/{tile_id}/storage-path",
    response_model=Dict[str, Optional[str]],
)
async def get_tile_storage_path(acquisition_id: str, tile_id: int):
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    if tile_id not in acquisition.tile_ids:
        raise HTTPException(
            status_code=404, detail="Tile not found in this acquisition"
        )

    tile = await Tile.get(tile_id)
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")

    current_location = acquisition.get_current_storage_location()
    storage_path = None
    if current_location and tile:
        storage_path = f"{current_location.base_path}/{tile.image_path}"

    return {"storage_path": storage_path}


@acquisition_api.delete(
    "/acquisitions/{acquisition_id}/tiles/{tile_id}", response_model=dict
)
async def delete_tile_from_acquisition(acquisition_id: str, tile_id: int):
    tile = Tile.find(Tile.acquisition_id == acquisition_id, Tile.tile_id == tile_id)
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")

    await tile.delete()

    return {
        "message": f"Tile {tile_id} from acquisition {acquisition_id} deleted successfully"
    }
