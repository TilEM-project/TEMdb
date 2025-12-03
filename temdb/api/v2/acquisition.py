import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import DBRef, ObjectId
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from pydantic import BaseModel
from pymongo import ASCENDING

from temdb.config import BaseConfig, get_config
from temdb.database import DatabaseManager
from temdb.dependencies import get_db_manager
from temdb.models.v2.acquisition import (
    Acquisition,
    AcquisitionCreate,
    AcquisitionStatus,
    AcquisitionUpdate,
    StorageLocation,
    StorageLocationCreate,
)
from temdb.models.v2.block import Block
from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.roi import ROI
from temdb.models.v2.section import Section
from temdb.models.v2.specimen import Specimen
from temdb.models.v2.substrate import Substrate
from temdb.models.v2.task import AcquisitionTask
from temdb.models.v2.tile import Tile, TileCreate


def serialize_mongo_doc(doc: Any) -> Any:
    if isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, DBRef):
        return {"collection": doc.collection, "id": str(doc.id)}
    elif isinstance(doc, dict):
        return {k: serialize_mongo_doc(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [serialize_mongo_doc(item) for item in doc]
    elif isinstance(doc, datetime):
        return doc.isoformat()
    return doc


acquisition_api = APIRouter(
    tags=["Acquisitions"],
)

logger = logging.getLogger(__name__)


class TileAcquisitionRefView(BaseModel):

    acquisition_ref: Optional[Any] = None

    class Settings:
        projection = {"acquisition_ref": 1, "_id": 0}


@acquisition_api.get("/acquisitions", response_model=Dict[str, Any])
async def list_acquisitions(
    response: Response,
    cursor: Optional[str] = Query(
        None,
        description="Cursor for pagination (e.g., last seen acquisition_id or _id)",
    ),
    limit: int = Query(50, ge=1, le=1000),
    sort_by: str = Query(
        "start_time", description="Field to sort by (e.g., start_time, acquisition_id)"
    ),
    sort_order: int = Query(-1, description="Sort order (-1=desc, 1=asc)"),
    specimen_id: Optional[str] = Query(
        None, description="Filter by human-readable Specimen ID"
    ),
    roi_id: Optional[str] = Query(None, description="Filter by human-readable ROI ID"),
    acquisition_task_id: Optional[str] = Query(
        None, description="Filter by human-readable Acquisition Task ID"
    ),
    montage_set_name: Optional[str] = Query(None),
    magnification: Optional[int] = Query(None, ge=1),
    status: Optional[AcquisitionStatus] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    param_tile_focus_lt: Optional[float] = Query(
        None,
        description="Filter acquisitions where tile focus score is less than this value",
    ),
    param_tile_match_quality_lt: Optional[float] = Query(
        None,
        description="Filter acquisitions where tile match quality is less than this value",
    ),
    param_tile_dx_gt: Optional[float] = Query(
        None, description="Filter acquisitions where tile dx is greater than this value"
    ),
    param_tile_dy_gt: Optional[float] = Query(
        None, description="Filter acquisitions where tile dy is greater than this value"
    ),
    fields: Optional[List[str]] = Query(
        None, description="Fields to return (e.g., ['acquisition_id', 'status'])"
    ),
) -> Dict[str, Any]:
    """Retrieve a list of acquisitions with filtering, sorting, and pagination."""
    try:
        main_filters = []

        if specimen_id:
            main_filters.append(Acquisition.specimen_id == specimen_id)
        if roi_id:
            main_filters.append(Acquisition.roi_id == roi_id)
        if acquisition_task_id:
            main_filters.append(Acquisition.acquisition_task_id == acquisition_task_id)
        if montage_set_name:
            main_filters.append(Acquisition.montage_set_name == montage_set_name)
        if magnification is not None:
            main_filters.append(
                Acquisition.acquisition_settings.magnification == magnification
            )
        if status:
            main_filters.append(Acquisition.status == status)

        if start_date and end_date:
            main_filters.append(Acquisition.start_time >= start_date)
            main_filters.append(Acquisition.start_time <= end_date)
        elif start_date:
            main_filters.append(Acquisition.start_time >= start_date)
        elif end_date:
            main_filters.append(Acquisition.start_time <= end_date)

        acq_ids_from_tile_filters = None
        tile_filter_active_and_processed = False

        if param_tile_focus_lt is not None:
            tile_filter_active_and_processed = True

            tiles_with_matching_focus_docs = (
                await Tile.find(Tile.focus_score < param_tile_focus_lt)
                .project(TileAcquisitionRefView)
                .to_list()
            )

            current_focus_acq_ids = {
                doc.acquisition_ref.id
                for doc in tiles_with_matching_focus_docs
                if hasattr(doc, "acquisition_ref") and doc.acquisition_ref
            }

            if acq_ids_from_tile_filters is None:
                acq_ids_from_tile_filters = current_focus_acq_ids
            else:
                acq_ids_from_tile_filters.intersection_update(current_focus_acq_ids)

        # TODO: Implement filtering for match_quality and dX/dY based on Tile.matcher array.

        if param_tile_match_quality_lt is not None:
            tile_filter_active_and_processed = True
            logger.warning(
                f"API parameter 'param_tile_match_quality_lt' ({param_tile_match_quality_lt}) is accepted but not yet implemented for filtering acquisitions."
            )

        if param_tile_dx_gt is not None:
            tile_filter_active_and_processed = True
            logger.warning(
                f"API parameter 'param_tile_dx_gt' ({param_tile_dx_gt}) is accepted but not yet implemented for filtering acquisitions."
            )

        if param_tile_dy_gt is not None:
            tile_filter_active_and_processed = True
            logger.warning(
                f"API parameter 'param_tile_dy_gt' ({param_tile_dy_gt}) is accepted but not yet implemented for filtering acquisitions."
            )

        if (
            tile_filter_active_and_processed
            and acq_ids_from_tile_filters is not None
            and not acq_ids_from_tile_filters
        ):
            metadata = {
                "total_count": 0,
                "returned_count": 0,
                "limit": limit,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "next_cursor": None,
            }
            return {"acquisitions": [], "metadata": metadata}

        if acq_ids_from_tile_filters is not None:
            main_filters.append(Acquisition.id.in_(list(acq_ids_from_tile_filters)))

        find_query = Acquisition.find(*main_filters, fetch_links=False)

        # Field projection
        projection = None
        if fields:
            projection = {field: 1 for field in fields}
            if "_id" not in fields:
                projection["_id"] = 1

        if projection:
            find_query = find_query.project(
                projection_model=None, projection=projection
            )

        sort_key = sort_by if sort_by else "start_time"
        sort_direction = sort_order if sort_order in [-1, 1] else -1
        find_query_for_list = find_query.sort([(sort_key, sort_direction)])

        total_count = await Acquisition.find(*main_filters).count()

        acquisitions_list = await find_query_for_list.limit(limit).to_list()

        next_cursor = str(acquisitions_list[-1].id) if acquisitions_list else None

        metadata = {
            "total_count": total_count,
            "returned_count": len(acquisitions_list),
            "limit": limit,
            "sort_by": sort_key,
            "sort_order": sort_direction,
            "next_cursor": next_cursor,
        }

        response.headers["Cache-Control"] = "private, max-age=300"
        response.headers["X-Total-Count"] = str(total_count)

        return {"acquisitions": acquisitions_list, "metadata": metadata}

    except Exception as e:
        logger.error(f"Error listing acquisitions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error retrieving acquisitions")


@acquisition_api.post(
    "/acquisitions", response_model=Acquisition, status_code=status.HTTP_201_CREATED
)
async def create_acquisition(
    acq_data: AcquisitionCreate, db_manager: DatabaseManager = Depends(get_db_manager)
):
    """Create a new acquisition with validation but without transactions."""
    new_acq_id_internal = None

    try:
        if await Acquisition.find_one({"acquisition_id": acq_data.acquisition_id}):
            raise HTTPException(
                400,
                f"Acquisition ID '{acq_data.acquisition_id}' already exists.",
            )

        roi = await ROI.find_one(ROI.roi_id == acq_data.roi_id, fetch_links=True)
        if not roi:
            raise HTTPException(404, f"ROI '{acq_data.roi_id}' not found.")

        task = await AcquisitionTask.find_one(
            AcquisitionTask.task_id == acq_data.acquisition_task_id,
            fetch_links=True,
        )
        if not task:
            raise HTTPException(
                404,
                f"Acquisition Task '{acq_data.acquisition_task_id}' not found.",
            )

        if task.roi_ref.id != roi.id:
            raise HTTPException(
                400,
                f"ROI ID '{roi.roi_id}' does not match ROI reference in Task '{task.task_id}'.",
            )

        specimen_ref_id = task.specimen_ref.id
        specimen_id_hr = task.specimen_id

        replaces_acq_ref_id = None
        if acq_data.replaces_acquisition_id:
            prev_acq = await Acquisition.find_one(
                {"acquisition_id": acq_data.replaces_acquisition_id},
            )
            if not prev_acq:
                raise HTTPException(
                    404,
                    f"Acquisition to replace ID '{acq_data.replaces_acquisition_id}' not found.",
                )
            replaces_acq_ref_id = prev_acq.id

        new_acquisition = Acquisition(
            acquisition_id=acq_data.acquisition_id,
            montage_id=acq_data.montage_id,
            specimen_id=specimen_id_hr,
            roi_id=roi.roi_id,
            acquisition_task_id=task.task_id,
            specimen_ref=specimen_ref_id,
            roi_ref=roi.id,
            acquisition_task_ref=task.id,
            hardware_settings=acq_data.hardware_settings,
            acquisition_settings=acq_data.acquisition_settings,
            calibration_info=acq_data.calibration_info,
            status=acq_data.status,
            tilt_angle=acq_data.tilt_angle,
            lens_correction=acq_data.lens_correction,
            start_time=acq_data.start_time or datetime.now(timezone.utc),
            end_time=acq_data.end_time,
            montage_set_name=acq_data.montage_set_name,
            sub_region=acq_data.sub_region,
            replaces_acquisition_ref=replaces_acq_ref_id,
        )
        insert_result = await new_acquisition.insert()
        new_acq_id_internal = insert_result.id

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        else:
            logger.error(
                f"Error during acquisition creation: {e}",
                exc_info=True,
            )
            raise HTTPException(500, "Failed to create acquisition.")

    if new_acq_id_internal:
        created_acq = await Acquisition.get(new_acq_id_internal, fetch_links=True)
        if created_acq:
            return created_acq
    raise HTTPException(500, "Failed to retrieve created acquisition after creation.")


@acquisition_api.get("/acquisitions/{acquisition_id}", response_model=Acquisition)
async def get_acquisition(acquisition_id: str):
    """Retrieve a specific acquisition by its human-readable ID."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id, fetch_links=True
    )
    if not acquisition:
        raise HTTPException(
            status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found"
        )
    return acquisition


@acquisition_api.patch("/acquisitions/{acquisition_id}", response_model=Acquisition)
async def update_acquisition(
    acquisition_id: str, updated_fields: AcquisitionUpdate = Body(...)
):
    """Update details of a specific acquisition."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(
            status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found"
        )

    update_data = updated_fields.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(400, "No update data provided")

    needs_save = False
    for field, value in update_data.items():
        # TODO: Handle nested updates for settings/calibration carefully
        if hasattr(acquisition, field) and getattr(acquisition, field) != value:
            setattr(acquisition, field, value)
            needs_save = True

    if needs_save:
        await acquisition.save()

    updated_acq = await Acquisition.get(acquisition.id, fetch_links=True)
    return updated_acq


@acquisition_api.delete(
    "/acquisitions/{acquisition_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_acquisition(acquisition_id: str):
    """Delete a specific acquisition."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(
            status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found"
        )

    tile_count = await Tile.find(Tile.acquisition_ref.id == acquisition.id).count()
    if tile_count > 0:
        raise HTTPException(
            400,
            f"Cannot delete acquisition '{acquisition_id}': {tile_count} tiles exist.",
        )

    await acquisition.delete()
    return None


@acquisition_api.post(
    "/acquisitions/{acquisition_id}/tiles",
    response_model=Tile,
    status_code=status.HTTP_201_CREATED,
)
async def add_tile_to_acquisition(acquisition_id: str, tile_data: TileCreate):
    """Add a single tile to an acquisition."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(
            status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found"
        )

    if await Tile.find_one(Tile.tile_id == tile_data.tile_id):
        raise HTTPException(400, f"Tile ID '{tile_data.tile_id}' already exists.")

    new_tile = Tile(
        **tile_data.model_dump(),
        acquisition_id=acquisition.acquisition_id,
        acquisition_ref=acquisition.id,
        roi_id=acquisition.roi_id,
        specimen_id=acquisition.specimen_id,
    )
    await new_tile.insert()
    return new_tile


@acquisition_api.post("/acquisitions/{acquisition_id}/tiles/bulk", response_model=dict)
async def add_tiles_to_acquisition(
    acquisition_id: str,
    tiles: List[TileCreate],
    db_manager: DatabaseManager = Depends(get_db_manager),
):
    """Add multiple tiles to an acquisition."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")

    total_tiles = len(tiles)
    collection = db_manager.db["tiles"]
    logger.info(f"Received {total_tiles} tiles for acquisition {acquisition_id}")

    incoming_tile_ids = [t.tile_id for t in tiles]
    existing_cursor = collection.find(
        {"tile_id": {"$in": incoming_tile_ids}},
        {"tile_id": 1}
    )
    existing_ids = {doc["tile_id"] async for doc in existing_cursor}

    acquisition_ref = DBRef("acquisitions", acquisition.id)

    docs_to_insert = [
        {
            "_id": ObjectId(),
            **tile.model_dump(),
            "acquisition_id": acquisition.acquisition_id,
            "acquisition_ref": acquisition_ref,
            "roi_id": acquisition.roi_id,
            "specimen_id": acquisition.specimen_id,
        }
        for tile in tiles
        if tile.tile_id not in existing_ids
    ]

    inserted_count = 0
    skipped_count = len(existing_ids)

    if docs_to_insert:
        try:
            result = await collection.insert_many(docs_to_insert, ordered=False)
            inserted_count = len(result.inserted_ids)
            logger.info(
                f"Inserted {inserted_count} tiles for acquisition {acquisition_id}"
            )
        except Exception as e:
            logger.error(
                f"Error inserting tiles for acquisition {acquisition_id}: {e}",
                exc_info=True,
            )
            raise HTTPException(500, f"Error inserting tiles: {e}")

    return {
        "acquisition_id": acquisition_id,
        "total_received": total_tiles,
        "inserted": inserted_count,
        "skipped_existing": skipped_count,
    }


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/tiles", response_model=Dict[str, Any]
)
async def get_tiles_from_acquisition(
    response: Response,
    acquisition_id: str,
    cursor: Optional[int] = Query(None, description="Last raster_index seen"),
    limit: int = Query(100, ge=1, le=1000),
    fields: Optional[List[str]] = Query(None),
):
    """Retrieve tiles associated with a specific acquisition."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")

    # Build base query with Beanie syntax for Link field
    filters = [Tile.acquisition_ref.id == acquisition.id]
    if cursor is not None:
        filters.append(Tile.raster_index > cursor)

    projection = None
    if fields:
        projection = {field: 1 for field in fields}
        if "raster_index" not in fields:
            projection["raster_index"] = 1
        projection["_id"] = 0

    find_query = Tile.find(*filters, fetch_links=False)

    if projection:
        find_query = find_query.project(projection_model=None, projection=projection)

    find_query = find_query.sort([("raster_index", ASCENDING)])

    tiles_list = await find_query.limit(limit).to_list()
    # Handle both Tile objects (no projection) and dicts (with projection)
    if tiles_list:
        last_tile = tiles_list[-1]
        next_cursor = last_tile["raster_index"] if isinstance(last_tile, dict) else last_tile.raster_index
    else:
        next_cursor = None

    has_more = (
        await Tile.find(*filters)
        .sort(("raster_index", ASCENDING))
        .skip(limit)
        .limit(1)
        .to_list()
    )

    has_more = len(has_more) > 0

    response.headers["Cache-Control"] = "private, max-age=300"

    return {
        "tiles": tiles_list,
        "metadata": {
            "returned_count": len(tiles_list),
            "limit": limit,
            "current_cursor": cursor,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/tiles/{tile_id}", response_model=Tile
)
async def get_tile_from_acquisition(acquisition_id: str, tile_id: str):
    """Retrieve a specific tile by its human-readable ID, verifying acquisition parent."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")

    tile = await Tile.find_one(
        {"tile_id": tile_id, "acquisition_id": acquisition.acquisition_id},
        fetch_links=True,
    )

    if not tile:
        raise HTTPException(
            404, f"Tile ID '{tile_id}' not found in acquisition '{acquisition_id}'"
        )
    return tile


acquisition_api.post(
    "/acquisitions/{acquisition_id}/storage-locations", response_model=Acquisition
)


async def add_storage_location(
    acquisition_id: str, storage_location: StorageLocationCreate
):
    """Add a storage location entry to an acquisition."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")

    new_location_data = storage_location.model_dump()
    make_current = new_location_data.pop("is_current", True)

    new_location = StorageLocation(
        **new_location_data,
        is_current=make_current,
        date_added=datetime.now(timezone.utc),
    )

    if make_current:
        for loc in acquisition.storage_locations:
            loc.is_current = False

    acquisition.storage_locations.append(new_location)
    await acquisition.save()
    updated_acq = await Acquisition.get(acquisition.id, fetch_links=True)
    return updated_acq


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/current-storage",
    response_model=Optional[StorageLocation],
)
async def get_current_storage_location(acquisition_id: str):
    """Get the current storage location for an acquisition."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    return acquisition.get_current_storage_location()


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/minimap-uri",
    response_model=Dict[str, Optional[str]],
)
async def get_minimap_uri(acquisition_id: str):
    """Get the calculated URI for the acquisition's minimap image."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    return {"minimap_uri": acquisition.get_minimap_uri()}


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/tile-count", response_model=Dict[str, int]
)
async def get_tile_count(acquisition_id: str):
    """Get the total count of tiles associated with an acquisition."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")
    tile_count = await Tile.find({"acquisition_id": acquisition_id}).count()
    return {"tile_count": tile_count}


@acquisition_api.delete(
    "/acquisitions/{acquisition_id}/tiles/{tile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_tile_from_acquisition(acquisition_id: str, tile_id: str):
    """Delete a specific tile, ensuring it belongs to the specified acquisition."""
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id
    )
    if not acquisition:
        raise HTTPException(404, f"Acquisition ID '{acquisition_id}' not found")

    tile = await Tile.find_one({"tile_id": tile_id, "acquisition_id": acquisition_id})

    if not tile:
        raise HTTPException(
            404, f"Tile ID '{tile_id}' not found in acquisition '{acquisition_id}'"
        )

    await tile.delete()
    return None


class AcquisitionFullMetadata(BaseModel):
    """Acquisition with complete hierarchy metadata"""

    acquisition: Acquisition
    acquisition_task: Optional[AcquisitionTask] = None
    roi: Optional[ROI] = None
    section: Optional[Section] = None
    cutting_session: Optional[CuttingSession] = None
    block: Optional[Block] = None
    specimen: Optional[Specimen] = None
    substrate: Optional[Substrate] = None


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/metadata", response_model=AcquisitionFullMetadata
)
async def get_acquisition_with_full_metadata(acquisition_id: str):
    """
    Retrieve an acquisition with its complete metadata.

    This endpoint returns the acquisition along with all related parent entities:
    specimen → block → cutting session → section → substrate → roi → acquisition_task → acquisition
    """
    acquisition = await Acquisition.find_one(
        Acquisition.acquisition_id == acquisition_id, fetch_links=True
    )
    if not acquisition:
        raise HTTPException(
            status_code=404, detail=f"Acquisition ID '{acquisition_id}' not found"
        )

    result = AcquisitionFullMetadata(acquisition=acquisition)

    if acquisition.acquisition_task_ref:
        task = await AcquisitionTask.get(
            acquisition.acquisition_task_ref.id, fetch_links=True
        )
        result.acquisition_task = task

        if task and task.roi_ref:
            roi = await ROI.get(task.roi_ref.id, fetch_links=True)
            result.roi = roi

            if roi and roi.section_ref:
                section = await Section.get(roi.section_ref.id, fetch_links=True)
                result.section = section

                if roi.substrate_media_id:
                    substrate = await Substrate.find_one(
                        Substrate.media_id == roi.substrate_media_id, fetch_links=True
                    )
                    result.substrate = substrate

                if section and section.cutting_session_ref:
                    cutting_session = await CuttingSession.get(
                        section.cutting_session_ref.id, fetch_links=True
                    )
                    result.cutting_session = cutting_session

                    if cutting_session and cutting_session.block_ref:
                        block = await Block.get(
                            cutting_session.block_ref.id, fetch_links=True
                        )
                        result.block = block

                        if block and block.specimen_ref:
                            specimen = await Specimen.get(
                                block.specimen_ref.id, fetch_links=True
                            )
                            result.specimen = specimen

    return result


@acquisition_api.get("/aggregated/acquisitions", response_model=Dict[str, Any])
async def list_acquisitions_with_hierarchy(
    response: Response,
    cursor: Optional[str] = Query(
        None,
        description="Cursor for pagination (e.g., last seen acquisition_id or _id)",
    ),
    limit: int = Query(50, ge=1, le=100),
    sort_by: str = Query(
        "start_time", description="Field to sort by (e.g., start_time, acquisition_id)"
    ),
    sort_order: int = Query(-1, description="Sort order (-1=desc, 1=asc)"),
    specimen_id: Optional[str] = Query(
        None, description="Filter by human-readable Specimen ID"
    ),
    roi_id: Optional[str] = Query(None, description="Filter by hierarchical ROI ID"),
    acquisition_task_id: Optional[str] = Query(
        None, description="Filter by human-readable Acquisition Task ID"
    ),
    substrate_media_id: Optional[str] = Query(
        None, description="Filter by substrate media ID"
    ),
    status: Optional[AcquisitionStatus] = Query(None),
) -> Dict[str, Any]:
    """
    Retrieve acquisitions with complete hierarchy metadata using MongoDB aggregation.

    This endpoint performs a comprehensive aggregation to include all hierarchy levels:
    specimen → block → cutting session → section → substrate → roi → acquisition_task → acquisition
    """
    try:
        match_filters = {}

        if specimen_id:
            match_filters["specimen_id"] = specimen_id
        if acquisition_task_id:
            match_filters["acquisition_task_id"] = acquisition_task_id
        if status:
            match_filters["status"] = status.value

        pipeline = []

        if match_filters:
            pipeline.append({"$match": match_filters})

        pipeline.extend(
            [
                {
                    "$lookup": {
                        "from": "acquisition_tasks",
                        "localField": "acquisition_task_ref.$id",
                        "foreignField": "_id",
                        "as": "task_info",
                    }
                },
                {"$unwind": {"path": "$task_info", "preserveNullAndEmptyArrays": True}},
            ]
        )

        # Lookup ROI
        pipeline.extend(
            [
                {
                    "$lookup": {
                        "from": "rois",
                        "localField": "roi_ref.$id",
                        "foreignField": "_id",
                        "as": "roi_info",
                    }
                },
                {"$unwind": {"path": "$roi_info", "preserveNullAndEmptyArrays": True}},
            ]
        )

        if roi_id:
            pipeline.append({"$match": {"roi_info.roi_id": roi_id}})
        if substrate_media_id:
            pipeline.append(
                {"$match": {"roi_info.substrate_media_id": substrate_media_id}}
            )

        pipeline.extend(
            [
                {
                    "$lookup": {
                        "from": "sections",
                        "localField": "roi_info.section_ref.$id",
                        "foreignField": "_id",
                        "as": "section_info",
                    }
                },
                {
                    "$unwind": {
                        "path": "$section_info",
                        "preserveNullAndEmptyArrays": True,
                    }
                },
            ]
        )

        # Lookup substrate
        pipeline.extend(
            [
                {
                    "$lookup": {
                        "from": "substrates",
                        "localField": "roi_info.substrate_media_id",
                        "foreignField": "media_id",
                        "as": "substrate_info",
                    }
                },
                {
                    "$unwind": {
                        "path": "$substrate_info",
                        "preserveNullAndEmptyArrays": True,
                    }
                },
            ]
        )

        pipeline.extend(
            [
                {
                    "$lookup": {
                        "from": "cutting_sessions",
                        "localField": "section_info.cutting_session_ref.$id",
                        "foreignField": "_id",
                        "as": "cutting_session_info",
                    }
                },
                {
                    "$unwind": {
                        "path": "$cutting_session_info",
                        "preserveNullAndEmptyArrays": True,
                    }
                },
            ]
        )

        pipeline.extend(
            [
                {
                    "$lookup": {
                        "from": "blocks",
                        "localField": "cutting_session_info.block_ref.$id",
                        "foreignField": "_id",
                        "as": "block_info",
                    }
                },
                {
                    "$unwind": {
                        "path": "$block_info",
                        "preserveNullAndEmptyArrays": True,
                    }
                },
            ]
        )

        pipeline.extend(
            [
                {
                    "$lookup": {
                        "from": "specimens",
                        "localField": "block_info.specimen_ref.$id",
                        "foreignField": "_id",
                        "as": "specimen_info",
                    }
                },
                {
                    "$unwind": {
                        "path": "$specimen_info",
                        "preserveNullAndEmptyArrays": True,
                    }
                },
            ]
        )

        sort_key = sort_by if sort_by else "start_time"
        sort_direction = sort_order if sort_order in [-1, 1] else -1
        pipeline.append({"$sort": {sort_key: sort_direction}})

        if cursor:
            pass

        pipeline.append({"$limit": limit})

        results = await Acquisition.aggregate(
            aggregation_pipeline=pipeline, projection_model=None
        ).to_list()

        count_pipeline = pipeline[:-1]
        count_pipeline.append({"$count": "total"})
        count_result = await Acquisition.aggregate(
            aggregation_pipeline=count_pipeline, projection_model=None
        ).to_list()

        total_count = count_result[0]["total"] if count_result else 0

        formatted_results = []
        for result in results:
            formatted_result = {
                "acquisition": serialize_mongo_doc(
                    {
                        k: v
                        for k, v in result.items()
                        if k
                        not in [
                            "task_info",
                            "roi_info",
                            "section_info",
                            "substrate_info",
                            "cutting_session_info",
                            "block_info",
                            "specimen_info",
                        ]
                    }
                ),
                "acquisition_task": serialize_mongo_doc(result.get("task_info")),
                "roi": serialize_mongo_doc(result.get("roi_info")),
                "section": serialize_mongo_doc(result.get("section_info")),
                "substrate": serialize_mongo_doc(result.get("substrate_info")),
                "cutting_session": serialize_mongo_doc(
                    result.get("cutting_session_info")
                ),
                "block": serialize_mongo_doc(result.get("block_info")),
                "specimen": serialize_mongo_doc(result.get("specimen_info")),
            }
            formatted_results.append(formatted_result)

        next_cursor = str(results[-1]["_id"]) if results else None

        metadata = {
            "total_count": total_count,
            "returned_count": len(formatted_results),
            "limit": limit,
            "sort_by": sort_key,
            "sort_order": sort_direction,
            "next_cursor": next_cursor,
        }

        response.headers["Cache-Control"] = "private, max-age=300"
        response.headers["X-Total-Count"] = str(total_count)

        return {"acquisitions": formatted_results, "metadata": metadata}

    except Exception as e:
        logger.error(f"Error in aggregated acquisitions query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Error retrieving aggregated acquisitions"
        )
