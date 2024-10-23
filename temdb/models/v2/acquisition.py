from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from beanie import Document, Link

from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.v2.enum_schemas import AcquisitionStatus
from temdb.models.v2.roi import ROI
from temdb.models.v2.imaging_session import ImagingSession
from temdb.models.v2.specimen import Specimen

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
    pixel_size: float
    rotation_angle: float
    lens_model: Optional[LensCorrectionModel]
    aperture_centroid: Optional[List[float]] = None


class HardwareParams(BaseModel):
    scope_id: str
    camera_model: str
    camera_serial: str
    bit_depth: int
    media_type: str


class AcquisitionParams(BaseModel):
    magnification: int
    spot_size: int
    exposure_time: int
    tile_size: List[int]
    tile_overlap: float


class AcquisitionCreate(BaseModel):
    version: str = "1.0"
    montage_id: str
    acquisition_id: str
    roi_id: int
    imaging_session_id: str
    hardware_settings: HardwareParams
    acquisition_settings: AcquisitionParams
    calibration_info: Optional[Calibration] = None
    status: AcquisitionStatus = AcquisitionStatus.PLANNED
    tilt_angle: float
    lens_correction: bool
    start_time: datetime
    end_time: Optional[datetime] = None
    montage_set_name: Optional[str] = None
    sub_region: Optional[Dict[str, int]] = None
    replaces_acquisition_id: Optional[int] = None


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
    replaces_acquisition_id: Optional[int] = None


class Acquisition(Document):
    metadata_version: str = "2.0"
    specimen_id: Link[Specimen]
    montage_id: str
    acquisition_id: str
    roi_id: Link[ROI]
    imaging_session_id: Link[ImagingSession]
    hardware_settings: HardwareParams
    acquisition_settings: AcquisitionParams
    calibration_info: Optional[Calibration] = None
    status: AcquisitionStatus
    tilt_angle: Optional[float] = None
    lens_correction: Optional[bool] = None
    start_time: datetime = None
    end_time: Optional[datetime] = None
    storage_locations: Optional[List[StorageLocation]] = Field(default_factory=list)
    montage_set_name: Optional[str] = None
    sub_region: Optional[Dict[str, int]] = None
    replaces_acquisition_id: Optional[int] = None
    version: int = 1

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

    @classmethod
    async def create_acquisition(cls, **kwargs):
        roi = kwargs.get("roi_id")
        latest_acquisition = await cls.find(
            Acquisition.roi_id == roi.id
        ).sort(-cls.version).first()
        if latest_acquisition:
            kwargs["version"] = latest_acquisition.version + 1
            kwargs["replaces_acquisition_id"] = latest_acquisition.id
        return await cls(**kwargs).insert()