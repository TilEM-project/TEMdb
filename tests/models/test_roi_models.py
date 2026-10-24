from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from temdb.models import ROICreate, ROICreatePayload, ROIPayload, ROIResponse, ROIUpdate, ROIUpdatePayload


class TestROICreate:
    def test_valid_roi_create(self):
        roi = ROICreate(
            section_id="SECTION001",
            created_at=datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc),
            payload=ROICreatePayload(vertices=[[0, 0], [10, 0], [10, 10]]),
        )
        assert roi.section_id == "SECTION001"
        assert roi.parent_created_at is None
        assert (roi.payload.rotation_angle, roi.payload.buffer_size) == (0.0, 0.0)

    def test_missing_vertices_is_rejected(self):
        with pytest.raises(ValidationError):
            ROICreate(section_id="SECTION001", created_at=datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc))

    @pytest.mark.parametrize("payload", [{"rotation_angle": 0.3}, {"vertices": [[0, 0], [10, 0]]}])
    def test_too_few_vertices_is_rejected(self, payload):
        """At least 3 vertices are required on create; rotation_angle and buffer_size default to 0."""
        with pytest.raises(ValidationError):
            ROICreatePayload(**payload)

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            ROICreate()

    def test_optional_fields(self):
        roi = ROICreate(
            created_at=datetime(2026, 10, 23, 10, 5, tzinfo=timezone.utc),
            section_id="SECTION001",
            parent_created_at=datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc),
            payload=ROICreatePayload(vertices=[[0, 0], [100, 0], [100, 100], [0, 100]], rotation_angle=0.0),
        )
        assert roi.parent_created_at == datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc)
        assert len(roi.payload.vertices) == 4


class TestROIUpdate:
    def test_all_fields_optional(self):
        update = ROIUpdate()
        assert update.payload.vertices is None

    def test_update_vertices(self):
        update = ROIUpdate(payload=ROIUpdatePayload(vertices=[[0, 0], [200, 0], [200, 200], [0, 200]]))
        assert len(update.payload.vertices) == 4

    @pytest.mark.parametrize("field", ["vertices", "rotation_angle", "buffer_size"])
    def test_patch_cannot_null_vertex_fields(self, field):
        """A PATCH cannot erase vertices, rotation_angle or buffer_size."""
        with pytest.raises(ValidationError):
            ROIUpdatePayload(**{field: None})


class TestROIResponse:
    def test_valid_response(self):
        response = ROIResponse(
            id=1,
            roi_id="MEDIA001.A0003.R001",
            section_id="SECTION001",
            substrate_media_id="MEDIA001",
            aperture_index=3,
            roi_number=1,
            created_at=datetime(2026, 10, 23, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime.now(),
            roi_payload=ROIPayload(vertices=[[0, 0], [100, 0], [100, 100], [0, 100]]),
        )
        assert response.roi_id == "MEDIA001.A0003.R001"
        assert len(response.roi_payload.vertices) == 4
