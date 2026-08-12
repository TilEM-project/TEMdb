from datetime import datetime

import pytest
from pydantic import ValidationError

from temdb.models import (
    SectionCreate,
    SectioningRunParameters,
    SectionMetric,
    SectionMetrics,
    SectionQuality,
    SectionResponse,
    SectionUpdate,
)


class TestSectionMetrics:
    def test_all_fields_optional(self):
        metrics = SectionMetrics()
        assert metrics.quality is None
        assert metrics.thickness_um is None
        assert metrics.thickness_consistency is None

    def test_with_all_fields(self):
        metrics = SectionMetrics(
            quality=SectionQuality.GOOD,
            thickness_um={"label": 50.0, "confidence": 0.95},
            knife_marks=SectionMetric(label=False, confidence=0.8),
        )
        assert metrics.quality == SectionQuality.GOOD
        assert metrics.thickness_um.label == 50.0
        assert metrics.thickness_um.confidence == 0.95
        assert metrics.knife_marks.label is False
        assert metrics.knife_marks.confidence == 0.8
        assert metrics.coverage is None

    def test_thickness_label_allows_any_type(self):
        metrics = SectionMetrics(thickness_um={"label": {"value": 50.0, "units": "um"}, "confidence": 0.9})
        assert metrics.thickness_um.label == {"value": 50.0, "units": "um"}


class TestSectionCreate:
    def test_valid_section_create(self):
        section = SectionCreate(
            cutting_session_id="CUT001",
            section_number=1,
            media_id="MEDIA001",
        )
        assert section.cutting_session_id == "CUT001"
        assert section.section_number == 1
        assert section.media_id == "MEDIA001"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            SectionCreate()

    def test_optional_fields(self):
        section = SectionCreate(
            cutting_session_id="CUT001",
            section_number=1,
            media_id="MEDIA001",
            barcode="BC123456",
            optical_image={
                "inspection": {
                    "image_path": "http://example.com/image.png",
                    "metadata": {"this": "that", "those": "these", "one": 2},
                },
            },
            section_metrics=SectionMetrics(quality=SectionQuality.GOOD),
            run_parameters=SectioningRunParameters(cutting_thickness_um=50.0, water_added=True),
        )
        assert section.barcode == "BC123456"
        assert section.section_metrics.quality == SectionQuality.GOOD
        assert section.run_parameters.cutting_thickness_um == 50.0
        assert section.run_parameters.water_added is True


class TestSectionUpdate:
    def test_all_fields_optional(self):
        update = SectionUpdate()
        assert update.section_metrics is None

    def test_update_quality(self):
        update = SectionUpdate(section_metrics=SectionMetrics(quality=SectionQuality.BROKEN))
        assert update.section_metrics.quality == SectionQuality.BROKEN

    def test_update_run_parameters(self):
        update = SectionUpdate(run_parameters=SectioningRunParameters(cut_cycle=2.3))
        assert update.run_parameters.cut_cycle == 2.3


class TestSectionResponse:
    def test_valid_response(self):
        response = SectionResponse(
            id=1,
            section_id="MEDIA001_S00001",
            cutting_session_id="CUT001",
            section_number=1,
            media_id="MEDIA001",
            block_id="BLOCK001",
            specimen_id="SPEC001",
            timestamp=datetime.now(),
        )
        assert response.section_id == "MEDIA001_S00001"
        assert response.section_number == 1
