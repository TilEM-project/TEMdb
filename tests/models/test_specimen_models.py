from datetime import datetime

import pytest
from pydantic import ValidationError
from temdb.models import SpecimenBase, SpecimenCreate, SpecimenResponse, SpecimenUpdate


class TestSpecimenBase:
    def test_all_fields_optional(self):
        specimen = SpecimenBase()
        assert specimen.description is None
        assert specimen.specimen_images is None
        assert specimen.functional_imaging_metadata is None

    def test_with_all_fields(self):
        specimen = SpecimenBase(
            description="Test specimen",
            specimen_images={"image1.png", "image2.png"},
            functional_imaging_metadata={"key": "value"},
        )
        assert specimen.description == "Test specimen"
        assert "image1.png" in specimen.specimen_images
        assert specimen.functional_imaging_metadata == {"key": "value"}

    def test_extra_fields_allowed(self):
        specimen = SpecimenBase(custom_field="custom_value")
        assert specimen.custom_field == "custom_value"


class TestSpecimenCreate:
    def test_valid_specimen_create(self):
        specimen = SpecimenCreate(
            specimen_id="SPEC001",
            description="Test specimen",
        )
        assert specimen.specimen_id == "SPEC001"
        assert specimen.description == "Test specimen"

    def test_specimen_id_required(self):
        with pytest.raises(ValidationError):
            SpecimenCreate()

    def test_minimal_specimen_create(self):
        specimen = SpecimenCreate(specimen_id="SPEC002")
        assert specimen.specimen_id == "SPEC002"
        assert specimen.description is None


class TestSpecimenUpdate:
    def test_all_fields_optional(self):
        update = SpecimenUpdate()
        assert update.description is None

    def test_partial_update(self):
        update = SpecimenUpdate(description="Updated description")
        assert update.description == "Updated description"


class TestSpecimenResponse:
    def test_valid_response(self):
        response = SpecimenResponse(
            specimen_id="SPEC001",
            description="Test specimen",
            created_at=datetime.now(),
        )
        assert response.specimen_id == "SPEC001"
        assert response.created_at is not None

    def test_specimen_id_required(self):
        with pytest.raises(ValidationError):
            SpecimenResponse()
