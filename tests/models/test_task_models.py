import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from temdb.models import (
    AcquisitionTaskCreate,
    AcquisitionTaskResponse,
    AcquisitionTaskUpdate,
)


class TestAcquisitionTaskCreate:
    def test_valid_task_create(self):
        task = AcquisitionTaskCreate(
            task_id="TASK001",
            specimen_id="SPEC001",
            block_id="BLOCK001",
            roi_id="ROI001",
        )
        assert task.roi_id == "ROI001"
        assert task.kind == "montage"
        assert task.task_id == "TASK001"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            AcquisitionTaskCreate()

    def test_montage_requires_lineage(self):
        with pytest.raises(ValidationError):
            AcquisitionTaskCreate(task_id="TASK001")

    def test_lens_correction_without_lineage(self):
        task = AcquisitionTaskCreate(task_id="TASK_LC_001", kind="lens_correction")
        assert task.roi_id is None
        assert task.specimen_id is None
        assert task.block_id is None

    def test_invalid_kind(self):
        with pytest.raises(ValidationError):
            AcquisitionTaskCreate(
                task_id="TASK001",
                specimen_id="SPEC001",
                block_id="BLOCK001",
                roi_id="ROI001",
                kind="alignment_task",
            )

    def test_tilt_series_fields(self):
        group = uuid.uuid4()
        task = AcquisitionTaskCreate(
            task_id="TASK001",
            specimen_id="SPEC001",
            block_id="BLOCK001",
            roi_id="ROI001",
            task_group_id=group,
            tilt_angle_deg=-15.0,
            sub_region={"x": 0, "y": 0, "width": 100, "height": 100},
        )
        assert task.task_group_id == group
        assert task.tilt_angle_deg == -15.0
        assert task.sub_region["width"] == 100

    def test_optional_fields(self):
        task = AcquisitionTaskCreate(
            task_id="TASK001",
            specimen_id="SPEC001",
            block_id="BLOCK001",
            roi_id="ROI001",
            tags=["urgent", "calibration"],
            metadata={"notes": "test task"},
        )
        assert "urgent" in task.tags


class TestAcquisitionTaskUpdate:
    def test_all_fields_optional(self):
        update = AcquisitionTaskUpdate()
        assert update.kind is None
        assert update.tilt_angle_deg is None
        assert update.sub_region is None

    def test_update_metadata(self):
        update = AcquisitionTaskUpdate(metadata={"notes": "updated"})
        assert update.metadata == {"notes": "updated"}

    def test_update_valid_kind(self):
        update = AcquisitionTaskUpdate(kind="lens_correction")
        assert update.kind == "lens_correction"

    def test_update_invalid_kind_rejected(self):
        with pytest.raises(ValidationError):
            AcquisitionTaskUpdate(kind="bogus")


class TestAcquisitionTaskResponse:
    def test_valid_response(self):
        response = AcquisitionTaskResponse(
            task_id="TASK001",
            specimen_id="SPEC001",
            block_id="BLOCK001",
            roi_id="ROI001",
            kind="montage",
            status="pending",
            created_at=datetime.now(),
        )
        assert response.task_id == "TASK001"
        assert response.kind == "montage"
        assert response.status == "pending"
        assert response.superseded_by is None

    def test_lens_correction_response_without_lineage(self):
        response = AcquisitionTaskResponse(
            task_id="TASK_LC_001",
            kind="lens_correction",
            status="pending",
        )
        assert response.roi_id is None
