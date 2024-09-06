from datetime import datetime, timezone
from typing import List, Optional, Dict

from fastapi import APIRouter, Body, HTTPException, Query

from temdb.models.v2.acquisition import (
    Acquisition,
    AcquisitionCreate,
    AcquisitionUpdate,
    StorageLocation,
    StorageLocationCreate,
)
from temdb.models.v2.imaging_session import ImagingSession
from temdb.models.v2.roi import ROI
from temdb.models.v2.tile import Tile, TileCreate

acquisition_api = APIRouter(
    tags=["Acquisitions"],
)


@acquisition_api.get("/acquisitions", response_model=List[Acquisition])
async def list_acquisitions(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    montage_set_name: Optional[str] = Query(None),
    magnification: Optional[int] = Query(None),
):
    query = {}
    if montage_set_name:
        query["montage_set_name"] = montage_set_name
    if magnification is not None:
        query["acquisition_settings.magnification"] = magnification

    return await Acquisition.find(query).skip(skip).limit(limit).to_list()


@acquisition_api.post("/acquisitions", response_model=Acquisition)
async def create_acquisition(acquisition: AcquisitionCreate):
    roi = await ROI.find_one(ROI.roi_id == acquisition.roi_id)
    if not roi:
        raise HTTPException(status_code=404, detail="ROI not found")

    imaging_session = await ImagingSession.find_one(
        ImagingSession.session_id == acquisition.imaging_session_id
    )
    if not imaging_session:
        raise HTTPException(status_code=404, detail="Imaging session not found")

    new_acquisition = Acquisition(
        version=acquisition.version,
        montage_id=acquisition.montage_id,
        specimen_id=imaging_session.specimen_id,
        acquisition_id=acquisition.acquisition_id,
        roi_id=roi.id,
        imaging_session_id=imaging_session.id,
        hardware_settings=acquisition.hardware_settings,
        acquisition_settings=acquisition.acquisition_settings,  # Contains magnification
        calibration_info=acquisition.calibration_info,
        status=acquisition.status,
        tilt_angle=acquisition.tilt_angle,
        lens_correction=acquisition.lens_correction,
        start_time=datetime.now(timezone.utc),
        montage_set_name=acquisition.montage_set_name,
        sub_region=acquisition.sub_region,
        replaces_acquisition_id=acquisition.replaces_acquisition_id,
    )
    await new_acquisition.insert()
    return new_acquisition


@acquisition_api.get("/acquisitions/{acquisition_id}", response_model=Acquisition)
async def get_acquisition(acquisition_id: str):
    acquisition = await Acquisition.get(acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")
    return acquisition


@acquisition_api.patch("/acquisitions/{acquisition_id}", response_model=Acquisition)
async def update_acquisition(
    acquisition_id: str, updated_fields: AcquisitionUpdate = Body(...)
):
    existing_acquisition = await Acquisition.get(acquisition_id)
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
    acquisition = await Acquisition.get(acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    await acquisition.delete()
    return {"message": "Acquisition deleted successfully"}


@acquisition_api.post("/acquisitions/{acquisition_id}/tiles", response_model=Tile)
async def add_tile_to_acquisition(acquisition_id: str, tile: TileCreate):
    acquisition = await Acquisition.get(acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    # Create and insert the tile
    new_tile = Tile(
        tile_id=tile.tile_id,
        acquisition_id=acquisition.id,
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

    # Add the tile's ID to the acquisition
    acquisition.add_tile(new_tile.id)
    await acquisition.save()

    return new_tile


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/tiles/{tile_id}", response_model=Tile
)
async def get_tile_from_acquisition(acquisition_id: str, tile_id: int):
    acquisition = await Acquisition.get(acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    if tile_id not in acquisition.tile_ids:
        raise HTTPException(
            status_code=404, detail="Tile not found in this acquisition"
        )

    tile = await Tile.get(tile_id)
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")

    return tile


@acquisition_api.post(
    "/acquisitions/{acquisition_id}/storage-locations", response_model=Acquisition
)
async def add_storage_location(
    acquisition_id: str, storage_location: StorageLocationCreate
):
    acquisition = await Acquisition.get(acquisition_id)
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
    acquisition = await Acquisition.get(acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    return acquisition.get_current_storage_location()


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/minimap-uri",
    response_model=Dict[str, Optional[str]],
)
async def get_minimap_uri(acquisition_id: str):
    acquisition = await Acquisition.get(acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    return {"minimap_uri": acquisition.get_minimap_uri()}


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/tile-count", response_model=Dict[str, int]
)
async def get_tile_count(acquisition_id: str):
    acquisition = await Acquisition.get(acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    return {"tile_count": len(acquisition.tile_ids)}


@acquisition_api.get(
    "/acquisitions/{acquisition_id}/tiles/{tile_id}/storage-path",
    response_model=Dict[str, Optional[str]],
)
async def get_tile_storage_path(acquisition_id: str, tile_id: int):
    acquisition = await Acquisition.get(acquisition_id)
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
    acquisition = await Acquisition.get(acquisition_id)
    if not acquisition:
        raise HTTPException(status_code=404, detail="Acquisition not found")

    if tile_id not in acquisition.tile_ids:
        raise HTTPException(
            status_code=404, detail="Tile not found in this acquisition"
        )

    tile = await Tile.get(tile_id)
    if not tile:
        raise HTTPException(status_code=404, detail="Tile not found")

    await tile.delete()
    acquisition.tile_ids.remove(tile_id)
    await acquisition.save()

    return {"message": "Tile deleted successfully"}
