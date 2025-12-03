from datetime import datetime, timezone

from beanie import Document, Link
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel
from temdb.models import (
    AcquisitionBase,
    AcquisitionParams,
    AcquisitionStatus,
    HardwareParams,
    StorageLocation,
)

from .roi import ROIDocument
from .specimen import SpecimenDocument
from .task import AcquisitionTaskDocument


class AcquisitionDocument(Document, AcquisitionBase):
    """MongoDB document for acquisition data."""

    acquisition_id: str = Field(..., description="ID of acquisition")
    montage_id: str = Field(..., description="ID of montage")
    specimen_id: str = Field(..., description="ID of specimen")
    roi_id: str = Field(..., description="ID of region of interest")
    acquisition_task_id: str = Field(..., description="ID of acquisition task")

    specimen_ref: Link[SpecimenDocument] = Field(..., description="Internal link to the specimen document")
    roi_ref: Link[ROIDocument] = Field(..., description="Internal link to the region of interest document")
    acquisition_task_ref: Link[AcquisitionTaskDocument] = Field(
        ..., description="Internal link to the acquisition task document"
    )

    # Override base fields that are required in document
    hardware_settings: HardwareParams = Field(..., description="Hardware settings of acquisition")
    acquisition_settings: AcquisitionParams = Field(..., description="Acquisition settings of acquisition")
    status: AcquisitionStatus = Field(default=AcquisitionStatus.IMAGING, description="Status of acquisition")
    start_time: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Start time of acquisition",
    )

    class Settings:
        name = "acquisitions"
        indexes = [
            IndexModel(
                [("acquisition_id", ASCENDING)],
                unique=True,
                name="acquisition_id_index",
            ),
            IndexModel(
                [("montage_id", ASCENDING)],
                name="montage_id_index",
            ),
            IndexModel(
                [("specimen_id", ASCENDING)],
                name="specimen_id_index",
            ),
            IndexModel(
                [("roi_id", ASCENDING)],
                name="roi_id_index",
            ),
            IndexModel(
                [("acquisition_task_id", ASCENDING)],
                name="acquisition_task_id_index",
            ),
            IndexModel(
                [("roi_ref.id", ASCENDING), ("start_time", DESCENDING)],
                name="roi_ref_start_time_index",
            ),
            IndexModel(
                [("acquisition_task_ref.id", ASCENDING), ("start_time", DESCENDING)],
                name="task_ref_start_time_index",
            ),
            IndexModel(
                [("specimen_ref.id", ASCENDING), ("start_time", DESCENDING)],
                name="specimen_ref_start_time_index",
            ),
            IndexModel([("status", ASCENDING)], name="status_index"),
            IndexModel(
                [("lens_correction", ASCENDING), ("tilt_angle", ASCENDING)],
                name="lens_correction_tilt_angle_index",
                sparse=True,
            ),
            IndexModel([("montage_set_name", ASCENDING)], name="montage_set_index", sparse=True),
            IndexModel(
                [("acquisition_settings.magnification", ASCENDING)],
                name="magnification_index",
            ),
            IndexModel([("start_time", DESCENDING)], name="start_time_index"),
            IndexModel(
                [("replaces_acquisition_id", ASCENDING)],
                name="replaces_acq_id_index",
                sparse=True,
            ),
        ]

    def get_current_storage_location(self) -> StorageLocation | None:
        """Get the current storage location."""
        if not self.storage_locations:
            return None
        return next((loc for loc in self.storage_locations if loc.is_current), None)

    def get_minimap_uri(self):
        """Get the minimap URI."""
        current_location = self.get_current_storage_location()
        if current_location:
            return f"{current_location.base_path}/minimap.png"
        return None

    @classmethod
    async def create_acquisition(cls, **kwargs):
        """Create a new acquisition with versioning."""
        roi = kwargs.get("roi_id")
        latest_acquisition = await cls.find(AcquisitionDocument.roi_id == roi.id).sort(-cls.version).first()
        if latest_acquisition:
            kwargs["version"] = latest_acquisition.version + 1
            kwargs["replaces_acquisition_id"] = latest_acquisition.id
        return await cls(**kwargs).insert()
