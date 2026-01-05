from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from temdb.models.enums import AcquisitionStatus


class LensCorrectionModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int = Field(..., description="ID of lens correction model")
    type: str = Field(
        ...,
        description="Transform type as defined in Render Transform Spec",
    )
    class_name: str = Field(
        ...,
        description="Class name of lens correction model from mpicbg-compatible className",
    )
    data_string: str = Field(
        ...,
        description="Data string of lens correction model from mpicbg-compatible dataString",
    )


class Calibration(BaseModel):
    model_config = ConfigDict(extra="allow")

    pixel_size: float = Field(..., description="Pixel size in nm")
    rotation_angle: float = Field(..., description="Rotation angle in degrees")
    lens_model: LensCorrectionModel | None = Field(None, description="Lens correction model")
    aperture_centroid: list[float] | None = Field(None, description="Aperture centroid in stage coordinates in nm")


class HardwareParams(BaseModel):
    model_config = ConfigDict(extra="allow")

    scope_id: str = Field(..., description="ID of microscope")
    camera_model: str = Field(..., description="Model of camera")
    camera_serial: str = Field(..., description="Serial number of camera")
    camera_bit_depth: int = Field(..., description="Native bit depth of camera")
    media_type: str = Field(..., description="Type of substrate in microscope")


class AcquisitionParams(BaseModel):
    model_config = ConfigDict(extra="allow")

    magnification: int = Field(..., description="Magnification of acquisition")
    spot_size: int = Field(..., description="Spot size of acquisition")
    exposure_time: int = Field(..., description="Exposure time of camera in ms")
    tile_size: list[int] = Field(..., description="Shape of the image tile in pixels")
    tile_overlap: float = Field(..., description="Pixel overlap to neighboring tiles")
    saved_bit_depth: int = Field(..., description="Bit depth of saved image")


class StorageLocation(BaseModel):
    model_config = ConfigDict(extra="allow")

    location_type: str = Field(..., description="Type of storage location, e.g. local, s3, etc.")
    base_path: str = Field(..., description="Base path of storage location")
    is_current: bool = Field(..., description="Whether this is the current storage location")
    date_added: datetime = Field(..., description="Date storage location was added")
    metadata: dict[str, Any] = Field(..., description="Metadata of storage location")


class StorageLocationCreate(BaseModel):
    model_config = ConfigDict(extra="allow")

    location_type: str = Field(..., description="Type of storage location, e.g. local, s3, etc.")
    base_path: str = Field(..., description="Base path of storage location")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata of storage location")


class AcquisitionBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    hardware_settings: HardwareParams | None = None
    acquisition_settings: AcquisitionParams | None = None
    calibration_info: Calibration | None = None
    status: AcquisitionStatus | None = None
    tilt_angle: float | None = Field(None, description="Tilt angle of acquisition in degrees")
    lens_correction: bool | None = Field(None, description="Whether this acquisition is a lens correction calibration")
    end_time: datetime | None = Field(None, description="End time of acquisition")
    storage_locations: list[StorageLocation] | None = Field(None, description="Storage locations of acquisition")
    montage_set_name: str | None = Field(None, description="Name of montage set")
    sub_region: dict[str, int] | None = Field(None, description="Sub region of acquisition")
    replaces_acquisition_id: int | None = Field(None, description="ID of acquisition this acquisition replaces")


class AcquisitionCreate(AcquisitionBase):
    acquisition_id: str = Field(..., description="Unique acquisition identifier")
    montage_id: str = Field(..., description="Montage identifier")
    roi_id: str = Field(..., description="ROI identifier")
    acquisition_task_id: str = Field(..., description="Parent task identifier")
    hardware_settings: HardwareParams = Field(..., description="Hardware settings of acquisition")
    acquisition_settings: AcquisitionParams = Field(..., description="Acquisition settings of acquisition")
    tilt_angle: float = Field(..., description="Tilt angle of acquisition in degrees")
    lens_correction: bool = Field(..., description="Whether this acquisition is a lens correction calibration")
    status: AcquisitionStatus = Field(default=AcquisitionStatus.IMAGING, description="Status of acquisition")
    start_time: datetime | None = Field(None, description="Start time of acquisition (defaults to now if not provided)")


class AcquisitionUpdate(AcquisitionBase):
    calibration_info: dict[str, Any] | None = Field(None, description="Calibration information of acquisition")


class AcquisitionResponse(AcquisitionBase):
    acquisition_id: str = Field(..., description="Unique acquisition identifier")
    montage_id: str = Field(..., description="Montage identifier")
    specimen_id: str = Field(..., description="Specimen identifier")
    roi_id: str = Field(..., description="ROI identifier")
    acquisition_task_id: str = Field(..., description="Parent task identifier")
    hardware_settings: HardwareParams = Field(..., description="Hardware settings of acquisition")
    acquisition_settings: AcquisitionParams = Field(..., description="Acquisition settings of acquisition")
    status: AcquisitionStatus = Field(..., description="Status of acquisition")
    start_time: datetime = Field(..., description="Start time of acquisition")

    created_at: datetime | None = None
    updated_at: datetime | None = None


class AcquisitionFullMetadata(BaseModel):
    """Acquisition with complete hierarchy metadata."""

    model_config = ConfigDict(extra="allow")

    acquisition: AcquisitionResponse
    task: dict[str, Any] | None = None
    roi: dict[str, Any] | None = None
    section: dict[str, Any] | None = None
    cutting_session: dict[str, Any] | None = None
    block: dict[str, Any] | None = None
    specimen: dict[str, Any] | None = None
    substrate: dict[str, Any] | None = None
