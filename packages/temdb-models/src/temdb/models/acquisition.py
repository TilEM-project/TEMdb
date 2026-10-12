import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from temdb.models.base import TEMDBModel
from temdb.models.enums import QC_STATES, RUN_STATUSES, TASK_KINDS, TRANSFER_STATES


class LensCorrectionModel(TEMDBModel):
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


class Calibration(TEMDBModel):
    pixel_size: float = Field(..., description="Pixel size in nm")
    rotation_angle: float = Field(..., description="Rotation angle in degrees")
    lens_model: LensCorrectionModel | None = Field(None, description="Lens correction model")
    aperture_centroid: list[float] | None = Field(None, description="Aperture centroid in stage coordinates in nm")


class HardwareParams(TEMDBModel):
    camera_model: str = Field(..., description="Model of camera")
    camera_serial: str = Field(..., description="Serial number of camera")
    camera_bit_depth: int = Field(..., description="Native bit depth of camera")
    media_type: str = Field(..., description="Type of substrate in microscope")


class AcquisitionParams(TEMDBModel):
    magnification: int = Field(..., description="Magnification of acquisition")
    spot_size: int = Field(..., description="Spot size of acquisition")
    exposure_time: int = Field(..., description="Exposure time of camera in ms")
    tile_size: list[int] = Field(..., description="Shape of the image tile in pixels")
    tile_overlap: float = Field(..., description="Pixel overlap to neighboring tiles")
    saved_bit_depth: int = Field(..., description="Bit depth of saved image")


class StorageLocation(TEMDBModel):
    location_type: str = Field(..., description="Type of storage location, e.g. local, s3, etc.")
    base_path: str = Field(..., description="Base path of storage location")
    is_current: bool = Field(..., description="Whether this is the current storage location")
    date_added: datetime = Field(..., description="Date storage location was added")
    metadata: dict[str, Any] = Field(..., description="Metadata of storage location")


class StorageLocationCreate(TEMDBModel):
    location_type: str = Field(..., description="Type of storage location, e.g. local, s3, etc.")
    base_path: str = Field(..., description="Base path of storage location")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata of storage location")


class AcquisitionBase(TEMDBModel):
    hardware_settings: HardwareParams | None = None
    acquisition_settings: AcquisitionParams | None = None
    calibration_info: Calibration | None = None
    tilt_angle_deg: float | None = Field(None, description="Tilt angle of acquisition in degrees")
    storage_locations: list[StorageLocation] | None = Field(None, description="Storage locations of acquisition")
    montage_set_name: str | None = Field(None, description="Name of montage set")
    sub_region: dict[str, int] | None = Field(None, description="Sub region of acquisition")
    replaces_acquisition_id: int | None = Field(None, description="ID of acquisition this acquisition replaces")


class AcquisitionCreate(AcquisitionBase):
    acquisition_id: str = Field(..., description="Unique acquisition identifier")
    montage_id: str = Field(..., description="Montage identifier")
    roi_id: str | None = Field(None, description="ROI identifier (required for montage runs)")
    acquisition_task_id: str = Field(..., description="Parent task identifier")
    microscope_id: uuid.UUID = Field(..., description="Microscope that executes this run")
    dataset_id: str | None = Field(None, description="Dataset this acquisition belongs to (UUIDv7)")
    kind: str = Field("montage", description="Run kind: montage or lens_correction")
    lc_id: uuid.UUID | None = Field(None, description="Lens correction applied to this run")
    hardware_settings: HardwareParams = Field(..., description="Hardware settings of acquisition")
    acquisition_settings: AcquisitionParams = Field(..., description="Acquisition settings of acquisition")
    start_time: datetime | None = Field(None, description="Start time of acquisition (defaults to now if not provided)")
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")

    @field_validator("kind")
    @classmethod
    def _kind_vocab(cls, v: str) -> str:
        if v not in TASK_KINDS:
            raise PydanticCustomError("value_error", f"kind must be one of {TASK_KINDS}")
        return v


class AcquisitionUpdate(AcquisitionBase):
    calibration_info: dict[str, Any] | None = Field(None, description="Calibration information of acquisition")
    status: str | None = Field(None, description="Terminal run status (write-once): complete, aborted, or failed")
    end_time: datetime | None = Field(None, description="End time of acquisition (set with terminal status)")
    error_message: str | None = Field(None, description="Failure detail for terminal status")
    qc_state: str | None = Field(None, description="QC axis state")
    transfer_state: str | None = Field(None, description="Transfer axis state")
    updated_by: str | None = Field(None, description="Actor stamped on qc_state/transfer_state changes")
    tile_count: int | None = Field(None, description="Rollup: total tiles")
    avg_focus_score: float | None = Field(None, description="Rollup: mean tile focus score")
    failed_tile_count: int | None = Field(None, description="Rollup: failed tiles")
    median_match_quality: float | None = Field(None, description="Rollup: median tile match quality")

    @field_validator("status")
    @classmethod
    def _status_terminal(cls, v: str | None) -> str:
        if v not in RUN_STATUSES:
            raise PydanticCustomError("value_error", f"status must be one of {RUN_STATUSES}")
        return v

    @field_validator("qc_state")
    @classmethod
    def _qc_state_vocab(cls, v: str | None) -> str:
        if v not in QC_STATES:
            raise PydanticCustomError("value_error", f"qc_state must be one of {QC_STATES}")
        return v

    @field_validator("transfer_state")
    @classmethod
    def _transfer_state_vocab(cls, v: str | None) -> str:
        if v not in TRANSFER_STATES:
            raise PydanticCustomError("value_error", f"transfer_state must be one of {TRANSFER_STATES}")
        return v


class AcquisitionResponse(AcquisitionBase):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    id: int = Field(..., description="Internal database ID")
    acquisition_id: str = Field(..., description="Unique acquisition identifier")
    run_id: uuid.UUID = Field(..., description="DB-minted UUIDv7 execution key")
    montage_id: str = Field(..., description="Montage identifier")
    specimen_id: str | None = Field(None, description="Specimen identifier")
    roi_id: str | None = Field(None, description="ROI identifier")
    acquisition_task_id: str = Field(..., description="Parent task identifier")
    microscope_id: uuid.UUID = Field(..., description="Microscope that executed this run")
    dataset_id: uuid.UUID | None = Field(None, description="Dataset this acquisition belongs to (UUIDv7)")
    kind: str = Field(..., description="Run kind: montage or lens_correction")
    lc_id: uuid.UUID | None = Field(None, description="Lens correction applied to this run")
    hardware_settings: HardwareParams = Field(..., description="Hardware settings of acquisition")
    acquisition_settings: AcquisitionParams = Field(..., description="Acquisition settings of acquisition")
    replaces_acquisition_id: str | None = Field(
        None, description="Business ID (acquisition_id) of acquisition this acquisition replaces"
    )
    status: str | None = Field(None, description="Terminal run status; null while in flight")
    error_message: str | None = Field(None, description="Failure detail for terminal status")
    qc_state: str = Field(..., description="QC axis state")
    qc_state_updated_at: datetime | None = None
    qc_state_updated_by: str | None = None
    transfer_state: str = Field(..., description="Transfer axis state")
    transfer_state_updated_at: datetime | None = None
    transfer_state_updated_by: str | None = None
    tile_count: int | None = None
    avg_focus_score: float | None = None
    failed_tile_count: int | None = None
    median_match_quality: float | None = None
    start_time: datetime = Field(..., description="Start time of acquisition")
    end_time: datetime | None = Field(None, description="End time of acquisition")

    created_at: datetime | None = None
    updated_at: datetime | None = None


class AcquisitionFullMetadata(TEMDBModel):
    """Acquisition with complete hierarchy metadata."""

    model_config = ConfigDict(from_attributes=True, extra="ignore", populate_by_name=True)

    acquisition: AcquisitionResponse
    task: dict[str, Any] | None = Field(None, alias="acquisition_task")
    roi: dict[str, Any] | None = None
    section: dict[str, Any] | None = None
    cutting_session: dict[str, Any] | None = None
    block: dict[str, Any] | None = None
    specimen: dict[str, Any] | None = None
    substrate: dict[str, Any] | None = None
