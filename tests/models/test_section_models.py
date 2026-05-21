from datetime import datetime

import pytest
from pydantic import ValidationError

from temdb.models import (
    QCCriterion,
    QCResult,
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


class TestQCResult:
    def test_accepts_heterogeneous_criteria(self):
        qc = QCResult(
            criteria={
                "coverage": QCCriterion(label="full_section", pass_status=True, conf=0.98),
                "shape": QCCriterion(label="Hexagon", pass_status=True, metric=6, message="vertices=6"),
            }
        )
        metrics = SectionMetrics(qc_result=qc)
        roundtrip = SectionMetrics.model_validate(metrics.model_dump(mode="json"))

        assert roundtrip.qc_result.criteria["coverage"].conf == 0.98
        assert roundtrip.qc_result.criteria["coverage"].metric is None
        assert roundtrip.qc_result.criteria["shape"].metric == 6
        assert roundtrip.qc_result.criteria["shape"].conf is None

    def test_criterion_allows_unknown_extra_fields(self):
        """extra='allow' lets LASSO add new per-criterion fields without breaking the model."""
        c = QCCriterion.model_validate(
            {
                "label": "x",
                "pass_status": True,
                "conf": 0.5,
                "future_field": "from_a_newer_lasso_version",
            }
        )
        assert c.model_dump()["future_field"] == "from_a_newer_lasso_version"
