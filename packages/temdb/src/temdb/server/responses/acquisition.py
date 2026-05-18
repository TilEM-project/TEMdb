from __future__ import annotations

from datetime import datetime
from typing import Any

from beanie.odm.fields import PydanticObjectId
from pydantic import BaseModel, ConfigDict, Field

from temdb.models import (
    AcquisitionParams,
    AcquisitionStatus,
    HardwareParams,
    StorageLocation,
)
from temdb.server.documents import AcquisitionDocument


class AcquisitionRead(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: PydanticObjectId = Field(..., alias="_id")
    acquisition_id: str
    montage_id: str
    specimen_id: str
    roi_id: str
    acquisition_task_id: str
    status: AcquisitionStatus
    start_time: datetime
    end_time: datetime | None = None
    hardware_settings: HardwareParams
    acquisition_settings: AcquisitionParams
    storage_locations: list[StorageLocation] | None = None
    lens_correction: bool | None = None
    tilt_angle: float | None = None
    montage_set_name: str | None = None
    sub_region: dict[str, Any] | None = None
    calibration_info: dict[str, Any] | None = None
    replaces_acquisition_id: str | None = None
    version: int | None = None
    specimen_ref: PydanticObjectId | None
    roi_ref: PydanticObjectId | None
    acquisition_task_ref: PydanticObjectId | None

    @classmethod
    def from_doc(cls, doc: AcquisitionDocument) -> "AcquisitionRead":
        return cls(
            _id=doc.id,
            acquisition_id=doc.acquisition_id,
            montage_id=doc.montage_id,
            specimen_id=doc.specimen_id,
            roi_id=doc.roi_id,
            acquisition_task_id=doc.acquisition_task_id,
            status=doc.status,
            start_time=doc.start_time,
            end_time=getattr(doc, "end_time", None),
            hardware_settings=doc.hardware_settings,
            acquisition_settings=doc.acquisition_settings,
            storage_locations=getattr(doc, "storage_locations", None),
            lens_correction=getattr(doc, "lens_correction", None),
            tilt_angle=getattr(doc, "tilt_angle", None),
            montage_set_name=getattr(doc, "montage_set_name", None),
            sub_region=getattr(doc, "sub_region", None),
            calibration_info=getattr(doc, "calibration_info", None),
            replaces_acquisition_id=(
                str(doc.replaces_acquisition_id)
                if getattr(doc, "replaces_acquisition_id", None) is not None
                else None
            ),
            version=getattr(doc, "version", None),
            specimen_ref=doc.specimen_ref,
            roi_ref=doc.roi_ref,
            acquisition_task_ref=doc.acquisition_task_ref,
        )
