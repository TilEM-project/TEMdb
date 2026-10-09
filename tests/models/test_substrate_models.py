from datetime import datetime

import pytest
from pydantic import ValidationError

from temdb.models import SubstrateCreate, SubstrateResponse, SubstrateUpdate


class TestSubstrateCreate:
    def test_valid_substrate_create(self):
        substrate = SubstrateCreate(
            media_id="MEDIA001",
            substrate_layout_id="LAYOUT001",
            condition={0: "ok"},
        )
        assert substrate.media_id == "MEDIA001"
        assert substrate.substrate_layout_id == "LAYOUT001"
        assert substrate.condition == {0: "ok"}

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            SubstrateCreate()

    def test_layout_id_is_required(self):
        with pytest.raises(ValidationError, match="substrate_layout_id"):
            SubstrateCreate(media_id="MEDIA001")


class TestSubstrateUpdate:
    def test_all_fields_optional(self):
        update = SubstrateUpdate()
        assert update.condition is None

    def test_update_aperture_conditions(self):
        update = SubstrateUpdate(condition={2: "damaged"})
        assert update.condition == {2: "damaged"}


class TestSubstrateResponse:
    def test_valid_response(self):
        response = SubstrateResponse(
            id=1,
            media_id="MEDIA001",
            substrate_layout_id="LAYOUT001",
            condition={0: "ok"},
            created_at=datetime.now(),
        )
        assert response.media_id == "MEDIA001"
        assert response.substrate_layout_id == "LAYOUT001"
        assert response.condition == {0: "ok"}
