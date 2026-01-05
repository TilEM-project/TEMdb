from datetime import datetime

import pytest
from pydantic import ValidationError
from temdb.models import (
    CuttingSessionCreate,
    CuttingSessionResponse,
    CuttingSessionUpdate,
)


class TestCuttingSessionCreate:
    def test_valid_session_create(self):
        session = CuttingSessionCreate(
            cutting_session_id="CUT001",
            block_id="BLOCK001",
            start_time=datetime.now(),
            sectioning_device="Test Device",
            media_type="tape",
        )
        assert session.block_id == "BLOCK001"
        assert session.cutting_session_id == "CUT001"
        assert session.media_type == "tape"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            CuttingSessionCreate()

    def test_optional_fields(self):
        session = CuttingSessionCreate(
            cutting_session_id="CUT001",
            block_id="BLOCK001",
            start_time=datetime.now(),
            sectioning_device="Test Device",
            media_type="tape",
            operator="Test Operator",
            knife_id="KNIFE001",
        )
        assert session.operator == "Test Operator"
        assert session.knife_id == "KNIFE001"


class TestCuttingSessionUpdate:
    def test_all_fields_optional(self):
        update = CuttingSessionUpdate()
        assert update.end_time is None
        assert update.operator is None

    def test_update_end_time(self):
        update = CuttingSessionUpdate(end_time=datetime.now())
        assert update.end_time is not None


class TestCuttingSessionResponse:
    def test_valid_response(self):
        response = CuttingSessionResponse(
            cutting_session_id="CUT001",
            block_id="BLOCK001",
            specimen_id="SPEC001",
            sectioning_device="Test Device",
            media_type="tape",
            start_time=datetime.now(),
            created_at=datetime.now(),
        )
        assert response.cutting_session_id == "CUT001"
        assert response.block_id == "BLOCK001"
