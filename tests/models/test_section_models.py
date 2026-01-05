from datetime import datetime

import pytest
from pydantic import ValidationError
from temdb.models import (
    SectionCreate,
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
        assert metrics.tissue_confidence_score is None

    def test_with_all_fields(self):
        metrics = SectionMetrics(
            quality=SectionQuality.GOOD,
            thickness_um=50.0,
            tissue_confidence_score=0.95,
        )
        assert metrics.quality == SectionQuality.GOOD
        assert metrics.thickness_um == 50.0
        assert metrics.tissue_confidence_score == 0.95


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
            optical_image={"url": "http://example.com/image.png"},
            section_metrics=SectionMetrics(quality=SectionQuality.GOOD),
        )
        assert section.barcode == "BC123456"
        assert section.section_metrics.quality == SectionQuality.GOOD


class TestSectionUpdate:
    def test_all_fields_optional(self):
        update = SectionUpdate()
        assert update.section_metrics is None

    def test_update_quality(self):
        update = SectionUpdate(section_metrics=SectionMetrics(quality=SectionQuality.BROKEN))
        assert update.section_metrics.quality == SectionQuality.BROKEN


class TestSectionResponse:
    def test_valid_response(self):
        response = SectionResponse(
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
