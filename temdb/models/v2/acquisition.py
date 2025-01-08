from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from beanie import Document, Link

from pymongo import IndexModel, ASCENDING, DESCENDING

from temdb.models.v2.enum_schemas import AcquisitionStatus, MediaType
from temdb.models.v2.roi import ROI
from temdb.models.v2.imaging_session import ImagingSession
from temdb.models.v2.specimen import Specimen

class StorageLocation(BaseModel):
    location_type: str = Field(..., description="Type of storage location, e.g. local, s3, etc.")
    base_path: str = Field(..., description="Base path of storage location")
    is_current: bool = Field(..., description="Whether this is the current storage location")
    date_added: datetime = Field(..., description="Date storage location was added")
    metadata: Dict = Field(..., description="Metadata of storage location")


class StorageLocationCreate(BaseModel):
    location_type: str = Field(..., description="Type of storage location, e.g. local, s3, etc.")
    base_path: str = Field(..., description="Base path of storage location")
    metadata: Dict = Field(..., description="Metadata of storage location")


class LensCorrectionModel(BaseModel):
    id: int = Field(..., description="ID of lens correction model")
    type: str = Field(..., description="'Transform type as defined in Render Transform Spec. ie 'leaf' 'interpolated' 'list' 'ref'")
    class_name: str = Field(..., description="Class name of lens correction model from mpicbg-compatible className'")
    data_string: str = Field(..., description="Data string of lens correction model from mpicbg-compatible dataString'")


class Calibration(BaseModel):
    pixel_size: float = Field(..., description="Pixel size in nm")
    rotation_angle: float = Field(..., description="Rotation angle in degrees")
    lens_model: Optional[LensCorrectionModel] = Field(None, description="Lens correction model")
    aperture_centroid: Optional[List[float]] = Field(None, description="Aperture centroid in stage coordinates in nm")


class HardwareParams(BaseModel):
    scope_id: str = Field(..., description="ID of microscope")
    camera_model: str = Field(..., description="Model of camera")
    camera_serial: str = Field(..., description="Serial number of camera")
    camera_bit_depth: int = Field(..., description="Native bit depth of camera")
    media_type: MediaType = Field(..., description="Type of substrate in microscope")


class AcquisitionParams(BaseModel):
    magnification: int = Field(..., description="Magnification of acquisition")
    spot_size: int = Field(..., description="Spot size of acquisition")
    exposure_time: int = Field(..., description="Exposure time of camera in ms")
    tile_size: List[int] = Field(..., description="Size of tiles in pixels")
    tile_overlap: float = Field(..., description="Overlap of tiles in percent of tile size")
    saved_bit_depth: int = Field(..., description="Bit depth of saved image")


class AcquisitionCreate(BaseModel):
    montage_id: str = Field(..., description="ID of montage")
    acquisition_id: str = Field(..., description="ID of acquisition")
    roi_id: int = Field(..., description="ID of region of interest")
    imaging_session_id: str = Field(..., description="ID of imaging session")
    hardware_settings: HardwareParams = Field(..., description="Hardware settings of acquisition")
    acquisition_settings: AcquisitionParams = Field(..., description="Acquisition settings of acquisition")
    calibration_info: Optional[Calibration] = Field(None, description="Calibration information of acquisition")
    status: AcquisitionStatus = Field(default= AcquisitionStatus.PLANNED,  description="Status of acquisition")
    tilt_angle: float = Field(..., description="Tilt angle of acquisition in degrees")
    lens_correction: bool = Field(..., description="Whether this acquisition is a lens correction calibration") 
    start_time: datetime = Field(..., description="Start time of acquisition")
    end_time: Optional[datetime] = Field(None, description="End time of acquisition")
    montage_set_name: Optional[str] = Field(None, description="Name of montage set")
    sub_region: Optional[Dict[str, int]] = Field(None, description="Sub region of acquisition")
    replaces_acquisition_id: Optional[int] = Field(None, description="ID of acquisition this acquisition replaces")


class AcquisitionUpdate(BaseModel):
    hardware_settings: Optional[HardwareParams] = Field(None, description="Hardware settings of acquisition")
    acquisition_settings: Optional[AcquisitionParams] = Field(None, description="Acquisition settings of acquisition")
    calibration_info: Optional[Dict] = Field(None, description="Calibration information of acquisition")
    status: Optional[AcquisitionStatus] = Field(None, description="Status of acquisition")
    tilt_angle: Optional[float] = Field(None, description="Tilt angle of acquisition in degrees")
    lens_correction: Optional[bool] = Field(None, description="Whether this acquisition is a lens correction calibration")
    end_time: Optional[datetime] = Field(None, description="End time of acquisition")
    montage_set_name: Optional[str] = Field(None, description="Name of montage set")
    sub_region: Optional[Dict[str, int]] = Field(None, description="Sub region of acquisition")
    replaces_acquisition_id: Optional[int] = Field(None, description="ID of acquisition this acquisition replaces")


class Acquisition(Document):
    specimen_id: Link[Specimen] = Field(..., description="ID of specimen")
    montage_id: str = Field(..., description="ID of montage")
    acquisition_id: str = Field(..., description="ID of acquisition")
    roi_id: Link[ROI] = Field(..., description="ID of region of interest")
    imaging_session_id: Link[ImagingSession] = Field(..., description="ID of imaging session")
    hardware_settings: HardwareParams = Field(..., description="Hardware settings of acquisition")
    acquisition_settings: AcquisitionParams = Field(..., description="Acquisition settings of acquisition")
    calibration_info: Optional[Calibration] = Field(None, description="Calibration information of acquisition")
    status: AcquisitionStatus = Field(default= AcquisitionStatus.PLANNED,  description="Status of acquisition")
    tilt_angle: Optional[float] = Field(None, description="Tilt angle of acquisition in degrees")
    lens_correction: Optional[bool] = Field(None, description="Whether this acquisition is a lens correction calibration")
    start_time: datetime = Field(..., description="Start time of acquisition")
    end_time: Optional[datetime] = Field(None, description="End time of acquisition")
    storage_locations: Optional[List[StorageLocation]] = Field(None, description="Storage locations of acquisition")
    montage_set_name: Optional[str] = Field(None, description="Name of montage set")
    sub_region: Optional[Dict[str, int]] = Field(None, description="Sub region of acquisition")
    replaces_acquisition_id: Optional[int] = Field(None, description="ID of acquisition this acquisition replaces")

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