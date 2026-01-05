from datetime import datetime, timezone

from beanie import Document, Link
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel
from temdb.models import AcquisitionTaskBase, AcquisitionTaskStatus

from .block import BlockDocument
from .roi import ROIDocument
from .specimen import SpecimenDocument


class AcquisitionTaskDocument(Document, AcquisitionTaskBase):
    """MongoDB document for acquisition task data."""

    task_id: str = Field(..., description="Unique identifier for this task")
    specimen_id: str = Field(..., description="ID of specimen")
    block_id: str = Field(..., description="ID of block")
    roi_id: str = Field(..., description="ID of region of interest to be acquired")

    # Override base fields with defaults for document
    task_type: str = Field("standard_acquisition", description="Type of acquisition task")
    version: int = Field(1, description="Version number of this task")
    status: AcquisitionTaskStatus = Field(default=AcquisitionTaskStatus.PLANNED)

    specimen_ref: Link[SpecimenDocument] = Field(..., description="Internal link to the specimen document")
    block_ref: Link[BlockDocument] = Field(..., description="Internal link to the block document")
    roi_ref: Link[ROIDocument] = Field(..., description="Internal link to the region of interest document")

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(None, description="When task was last updated")

    class Settings:
        name = "acquisition_tasks"
        indexes = [
            IndexModel([("task_id", ASCENDING)], unique=True, name="task_id_index"),
            IndexModel([("created_at", DESCENDING)], name="created_at_index"),
            IndexModel([("updated_at", DESCENDING)], name="updated_at_index"),
            IndexModel([("completed_at", DESCENDING)], name="completed_at_index"),
            IndexModel([("started_at", DESCENDING)], name="started_at_index"),
            IndexModel(
                [("task_id", ASCENDING), ("version", DESCENDING)],
                name="task_id_version_index",
            ),
            IndexModel([("status", ASCENDING)], name="status_index"),
            IndexModel(
                [("specimen_ref.id", ASCENDING), ("block_ref.id", ASCENDING)],
                name="specimen_block_ref_index",
            ),
            IndexModel([("roi_ref.id", ASCENDING)], name="roi_ref_index"),
            IndexModel([("task_type", ASCENDING)], name="task_type_index"),
            IndexModel([("tags", ASCENDING)], name="tags_index"),
        ]

    @classmethod
    async def get_latest_version(cls, task_id: str):
        """Get the latest version of a task by human-readable task_id."""
        return await cls.find(cls.task_id == task_id).sort([("version", -1)]).first_or_none()
