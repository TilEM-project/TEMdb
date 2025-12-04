from datetime import datetime

import pytest
from pydantic import ValidationError
from temdb.models import (
    AcquisitionTaskCreate,
    AcquisitionTaskResponse,
    AcquisitionTaskStatus,
    AcquisitionTaskUpdate,
)


class TestAcquisitionTaskCreate:
    def test_valid_task_create(self):
        task = AcquisitionTaskCreate(
            task_id="TASK001",
            specimen_id="SPEC001",
            block_id="BLOCK001",
            roi_id="ROI001",
            task_type="standard_acquisition",
        )
        assert task.roi_id == "ROI001"
        assert task.task_type == "standard_acquisition"
        assert task.task_id == "TASK001"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            AcquisitionTaskCreate()

    def test_optional_fields(self):
        task = AcquisitionTaskCreate(
            task_id="TASK001",
            specimen_id="SPEC001",
            block_id="BLOCK001",
            roi_id="ROI001",
            task_type="standard_acquisition",
            tags=["urgent", "calibration"],
            metadata={"notes": "test task"},
        )
        assert "urgent" in task.tags


class TestAcquisitionTaskUpdate:
    def test_all_fields_optional(self):
        update = AcquisitionTaskUpdate()
        assert update.status is None

    def test_update_status(self):
        update = AcquisitionTaskUpdate(status=AcquisitionTaskStatus.IN_PROGRESS)
        assert update.status == AcquisitionTaskStatus.IN_PROGRESS


class TestAcquisitionTaskResponse:
    def test_valid_response(self):
        response = AcquisitionTaskResponse(
            task_id="TASK001",
            specimen_id="SPEC001",
            block_id="BLOCK001",
            roi_id="ROI001",
            task_type="standard_acquisition",
            status=AcquisitionTaskStatus.PLANNED,
            version=1,
            created_at=datetime.now(),
        )
        assert response.task_id == "TASK001"
        assert response.status == AcquisitionTaskStatus.PLANNED
