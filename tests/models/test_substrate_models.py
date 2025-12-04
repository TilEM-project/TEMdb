from datetime import datetime

import pytest
from pydantic import ValidationError
from temdb.models import (
    Aperture,
    ReferencePoints,
    SubstrateCreate,
    SubstrateResponse,
    SubstrateUpdate,
)


class TestAperture:
    def test_valid_aperture(self):
        aperture = Aperture(
            uid="A1",
            index=0,
            status="available",
        )
        assert aperture.uid == "A1"
        assert aperture.index == 0
        assert aperture.status == "available"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            Aperture()


class TestReferencePoints:
    def test_valid_reference_points(self):
        ref = ReferencePoints(
            fiducial_1=[0.0, 0.0],
            fiducial_2=[100.0, 0.0],
            fiducial_3=[0.0, 100.0],
        )
        assert ref.fiducial_1 == [0.0, 0.0]


class TestSubstrateCreate:
    def test_valid_substrate_create(self):
        substrate = SubstrateCreate(
            media_id="MEDIA001",
            media_type="tape",
        )
        assert substrate.media_id == "MEDIA001"
        assert substrate.media_type == "tape"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            SubstrateCreate()

    def test_with_apertures(self):
        substrate = SubstrateCreate(
            media_id="WAFER001",
            media_type="wafer",
            apertures=[
                Aperture(uid="A1", index=0, status="available"),
                Aperture(uid="A2", index=1, status="available"),
            ],
        )
        assert len(substrate.apertures) == 2


class TestSubstrateUpdate:
    def test_all_fields_optional(self):
        update = SubstrateUpdate()
        assert update.status is None

    def test_update_status(self):
        update = SubstrateUpdate(status="in_use")
        assert update.status == "in_use"


class TestSubstrateResponse:
    def test_valid_response(self):
        response = SubstrateResponse(
            media_id="MEDIA001",
            media_type="tape",
            status="new",
            created_at=datetime.now(),
        )
        assert response.media_id == "MEDIA001"
        assert response.media_type == "tape"
