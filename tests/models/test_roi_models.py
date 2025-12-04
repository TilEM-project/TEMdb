from datetime import datetime

import pytest
from pydantic import ValidationError
from temdb.models import ROICreate, ROIResponse, ROIUpdate


class TestROICreate:
    def test_valid_roi_create(self):
        roi = ROICreate(
            section_id="SECTION001",
            specimen_id="SPEC001",
            block_id="BLOCK001",
            substrate_media_id="MEDIA001",
            roi_number=1,
        )
        assert roi.section_id == "SECTION001"
        assert roi.roi_number == 1
        assert roi.specimen_id == "SPEC001"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            ROICreate()

    def test_optional_fields(self):
        roi = ROICreate(
            section_id="SECTION001",
            specimen_id="SPEC001",
            block_id="BLOCK001",
            substrate_media_id="MEDIA001",
            roi_number=1,
            parent_roi_id="SPEC001.BLK001.SEC001.SUB001.ROI001",
            vertices=[[0, 0], [100, 0], [100, 100], [0, 100]],
        )
        assert roi.parent_roi_id == "SPEC001.BLK001.SEC001.SUB001.ROI001"
        assert len(roi.vertices) == 4


class TestROIUpdate:
    def test_all_fields_optional(self):
        update = ROIUpdate()
        assert update.vertices is None

    def test_update_vertices(self):
        update = ROIUpdate(vertices=[[0, 0], [200, 0], [200, 200], [0, 200]])
        assert len(update.vertices) == 4


class TestROIResponse:
    def test_valid_response(self):
        response = ROIResponse(
            roi_id="SPEC001.BLK001.SEC001.SUB001.ROI001",
            section_id="SECTION001",
            specimen_id="SPEC001",
            block_id="BLOCK001",
            substrate_media_id="MEDIA001",
            roi_number=1,
            hierarchy_level=1,
            updated_at=datetime.now(),
        )
        assert response.roi_id == "SPEC001.BLK001.SEC001.SUB001.ROI001"
        assert response.hierarchy_level == 1
