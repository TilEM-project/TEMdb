from datetime import datetime

import pytest
from pydantic import ValidationError

from temdb.models import SubstrateCreate, SubstrateResponse, SubstrateUpdate


class TestSubstrateCreate:
    def test_valid_substrate_create(self):
        substrate = SubstrateCreate(
            media_id="MEDIA001",
            substrate_layout_id="LAYOUT001",
            aperture_status=["available", "used"],
        )
        assert substrate.media_id == "MEDIA001"
        assert substrate.substrate_layout_id == "LAYOUT001"
        assert substrate.aperture_status == ["available", "used"]

    def test_unknown_aperture_status_is_rejected(self):
        with pytest.raises(ValidationError):
            SubstrateCreate(media_id="MEDIA001", substrate_layout_id="LAYOUT001", aperture_status=["ok"])

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            SubstrateCreate()

    def test_layout_id_is_required(self):
        with pytest.raises(ValidationError, match="substrate_layout_id"):
            SubstrateCreate(media_id="MEDIA001")


class TestSubstrateUpdate:
    def test_all_fields_optional(self):
        update = SubstrateUpdate()
        assert update.aperture_status is None

    def test_update_aperture_status_by_index(self):
        update = SubstrateUpdate(aperture_status={2: "damaged"})
        assert update.aperture_status == {2: "damaged"}


class TestSubstrateResponse:
    def test_valid_response(self):
        response = SubstrateResponse(
            id=1,
            media_id="MEDIA001",
            substrate_layout_id="LAYOUT001",
            aperture_status=["damaged"],
            created_at=datetime.now(),
        )
        assert response.media_id == "MEDIA001"
        assert response.substrate_layout_id == "LAYOUT001"
        assert response.aperture_status == ["damaged"]
