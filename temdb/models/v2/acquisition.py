from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from beanie import Document, Link, PydanticObjectId

from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.v2.enum_schemas import AcquisitionStatus
from temdb.models.v2.roi import ROI
from temdb.models.v2.imaging_session import ImagingSession
from temdb.models.v2.tile import Tile


class StorageLocation(BaseModel):
    location_type: str
    base_path: str
    is_current: bool = True
    date_added: datetime = None
    metadata: Dict = Field(default_factory=dict)


class StorageLocationCreate(BaseModel):
    location_type: str
    base_path: str
    metadata: Dict = {}


class LensCorrectionModel(BaseModel):
    id: int
    type: str
    class_name: str
    data_string: str


class Calibration(BaseModel):
    pixel_size: List[float]
    stig_angle: float
    lens_model: Optional[LensCorrectionModel]
    aperture_centroid: List[float]


class HardwareParams(BaseModel):
    scope_id: str
    camera_model: str
    camera_serial: str
    bit_depth: int
    media: str


class AcquisitionParams(BaseModel):
    magnification: int
    spot_size: int
    exposure_time: int
    tile_size: List[int]
    tile_overlap: List[int]


class AcquisitionCreate(BaseModel):
    version: str
    montage_id: str
    acquisition_id: str
    roi_id: PydanticObjectId
    imaging_session_id: PydanticObjectId
    hardware_settings: HardwareParams
    acquisition_settings: AcquisitionParams
    status: AcquisitionStatus
    tilt_angle: float
    lens_correction: bool
    montage_set_name: Optional[str] = None
    sub_region: Optional[Dict[str, int]] = None
    replaces_acquisition_id: Optional[PydanticObjectId] = None


class AcquisitionUpdate(BaseModel):
    hardware_settings: Optional[HardwareParams] = None
    acquisition_settings: Optional[AcquisitionParams] = None
    calibration_info: Optional[Dict] = None
    status: Optional[AcquisitionStatus] = None
    tilt_angle: Optional[float] = None
    lens_correction: Optional[bool] = None
    end_time: Optional[datetime] = None
    montage_set_name: Optional[str] = None
    sub_region: Optional[Dict[str, int]] = None
    replaces_acquisition_id: Optional[PydanticObjectId] = None


class Acquisition(Document):
    metadata_version: str = "1.0"
    montage_id: str
    acquisition_id: str
    roi_id: Link[ROI]
    imaging_session_id: Link[ImagingSession]
    hardware_settings: HardwareParams
    acquisition_settings: AcquisitionParams
    calibration_info: Calibration
    status: AcquisitionStatus
    tilt_angle: Optional[float] = None
    lens_correction: Optional[bool] = None
    start_time: datetime = None
    end_time: Optional[datetime] = None
    storage_locations: Optional[List[StorageLocation]] = Field(default_factory=list)
    tile_ids: Optional[List[Tile]] = Field(default_factory=list)
    montage_set_name: Optional[str] = None
    sub_region: Optional[Dict[str, int]] = None
    replaces_acquisition_id: Optional[PydanticObjectId] = None

    class Settings:
        name = "acquisitions"
        indexes = [
            IndexModel(
                [("acquisition_id", ASCENDING)],
                unique=True,
                name="acquisition_id_index",
            ),
            IndexModel(
                [("roi_id.id", ASCENDING), ("start_time", DESCENDING)],
                name="roi_start_time_index",
            ),
            IndexModel(
                [("imaging_session_id.id", ASCENDING), ("start_time", DESCENDING)],
                name="imaging_session_start_time_index",
            ),
            IndexModel([("status", ASCENDING)], name="status_index"),
            IndexModel(
                [("lens_correction", ASCENDING), ("tilt_angle", ASCENDING)],
                name="lens_correction_tilt_angle_index",
            ),
            IndexModel([("montage_set_name", ASCENDING)], name="montage_set_index"),
            IndexModel(
                [("acquisition_settings.magnification", ASCENDING)],
                name="magnification_index",
            ),
        ]

    def get_current_storage_location(self) -> Optional[StorageLocation]:
        return next((loc for loc in self.storage_locations if loc.is_current), None)

    def get_minimap_uri(self):
        current_location = self.get_current_storage_location()
        if current_location:
            return f"{current_location.base_path}/minimap.png"
        return None

    def get_tile_count(self) -> int:
        return len(self.tile_ids)

    async def get_tile_storage_path(self, tile_id: str):
        current_location = self.get_current_storage_location()
        tile = await Tile.get(tile_id)
        if current_location and tile:
            return f"{current_location.base_path}/{tile.relative_path}"
        return None

    def add_tile(self, tile_id: str):
        self.tile_ids.append(tile_id)

    async def get_tile(self, tile_id: str) -> Optional[Tile]:
        return await Tile.get(tile_id)
