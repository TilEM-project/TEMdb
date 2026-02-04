import logging

from fastapi import APIRouter, HTTPException, Query, Response
from pymongo import ASCENDING

from temdb.models import PaginatedTileResponse, TileResponse, TileSpecMetadata
from temdb.server.documents import (
    AcquisitionDocument as Acquisition,
)
from temdb.server.documents import (
    ROIDocument as ROI,
)
from temdb.server.documents import (
    SectionDocument as Section,
)
from temdb.server.documents import (
    TileDocument as Tile,
)

montage_api = APIRouter(tags=["Montages"])
logger = logging.getLogger(__name__)


@montage_api.get("/montages/{montage_id}/tilespec-metadata", response_model=TileSpecMetadata)
async def get_tilespec_metadata(response: Response, montage_id: str):
    """Get acquisition/hierarchy metadata for TileSpec generation."""
    acquisition = await Acquisition.find_one(Acquisition.montage_id == montage_id, fetch_links=True)
    if not acquisition:
        raise HTTPException(status_code=404, detail=f"Montage '{montage_id}' not found")

    response.headers["Cache-Control"] = "private, max-age=300"

    roi = await ROI.find_one(ROI.roi_id == acquisition.roi_id, fetch_links=True)
    if not roi:
        logger.warning(f"ROI '{acquisition.roi_id}' not found for montage '{montage_id}'")

    section = None
    if roi and roi.section_ref:
        section = await Section.get(roi.section_ref.id, fetch_links=True)
        if not section:
            logger.warning(f"Section not found for ROI '{roi.roi_id}'")

    calibration = acquisition.calibration_info
    pixel_size = 0.0
    rotation_angle = 0.0
    lens_model = None

    if calibration is not None:
        if isinstance(calibration, dict):
            pixel_size = calibration.get("pixel_size", 0.0)
            rotation_angle = calibration.get("rotation_angle", 0.0)
            lens_model = calibration.get("lens_model")
        else:
            pixel_size = getattr(calibration, "pixel_size", 0.0)
            rotation_angle = getattr(calibration, "rotation_angle", 0.0)
            lens_model = getattr(calibration, "lens_model", None)

    storage_base_path = None
    if acquisition.storage_locations:
        for loc in acquisition.storage_locations:
            if loc.is_current:
                storage_base_path = loc.base_path
                break

    return TileSpecMetadata(
        montage_id=montage_id,
        width=acquisition.acquisition_settings.tile_size[0],
        height=acquisition.acquisition_settings.tile_size[1],
        saved_bit_depth=acquisition.acquisition_settings.saved_bit_depth,
        pixel_size=pixel_size,
        rotation_angle=rotation_angle,
        lens_model=lens_model,
        scope_id=acquisition.hardware_settings.scope_id,
        camera_serial=acquisition.hardware_settings.camera_serial,
        section_id=section.section_id if section else "",
        section_number=section.section_number if section else 0,
        media_id=roi.substrate_media_id if roi else "",
        roi_id=acquisition.roi_id,
        specimen_id=acquisition.specimen_id,
        storage_base_path=storage_base_path,
        tilt_angle=acquisition.tilt_angle,
    )


@montage_api.get("/montages/{montage_id}/tiles", response_model=PaginatedTileResponse)
async def get_montage_tiles(
    response: Response,
    montage_id: str,
    cursor: int | None = Query(None, description="Last raster_index seen"),
    limit: int = Query(1000, ge=1, le=10000),
) -> PaginatedTileResponse:
    """Get paginated tiles for a montage."""
    acquisition = await Acquisition.find_one(Acquisition.montage_id == montage_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail=f"Montage '{montage_id}' not found")

    filters = [Tile.acquisition_ref.id == acquisition.id]
    if cursor is not None:
        filters.append(Tile.raster_index > cursor)

    tiles_docs = await Tile.find(*filters).sort([("raster_index", ASCENDING)]).limit(limit + 1).to_list()

    has_more = len(tiles_docs) > limit
    tiles_docs = tiles_docs[:limit]

    tiles = [
        TileResponse(
            tile_id=t.tile_id,
            acquisition_id=acquisition.acquisition_id,
            image_path=t.image_path,
            raster_position=t.raster_position,
            stage_position=t.stage_position,
            raster_index=t.raster_index,
            focus_score=t.focus_score,
            min_value=t.min_value,
            max_value=t.max_value,
            mean_value=t.mean_value,
            std_value=t.std_value,
        )
        for t in tiles_docs
    ]

    next_cursor = tiles[-1].raster_index if tiles else None

    response.headers["Cache-Control"] = "private, max-age=300"

    return PaginatedTileResponse(
        tiles=tiles,
        metadata={
            "returned_count": len(tiles),
            "limit": limit,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    )
