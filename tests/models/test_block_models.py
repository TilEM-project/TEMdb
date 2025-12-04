from datetime import datetime

import pytest
from pydantic import ValidationError
from temdb.models import BlockBase, BlockCreate, BlockResponse, BlockUpdate


class TestBlockBase:
    def test_all_fields_optional(self):
        block = BlockBase()
        assert block.microCT_info is None

    def test_with_microCT_info(self):
        block = BlockBase(microCT_info={"resolution": 1.5, "unit": "um"})
        assert block.microCT_info["resolution"] == 1.5
        assert block.microCT_info["unit"] == "um"

    def test_extra_fields_allowed(self):
        block = BlockBase(custom_field="custom_value")
        assert block.custom_field == "custom_value"


class TestBlockCreate:
    def test_valid_block_create(self):
        block = BlockCreate(
            block_id="BLOCK001",
            specimen_id="SPEC001",
            microCT_info={"resolution": 2.0},
        )
        assert block.block_id == "BLOCK001"
        assert block.specimen_id == "SPEC001"
        assert block.microCT_info["resolution"] == 2.0

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            BlockCreate()

        with pytest.raises(ValidationError):
            BlockCreate(block_id="BLOCK001")

        with pytest.raises(ValidationError):
            BlockCreate(specimen_id="SPEC001")

    def test_minimal_block_create(self):
        block = BlockCreate(block_id="BLOCK002", specimen_id="SPEC001")
        assert block.block_id == "BLOCK002"
        assert block.specimen_id == "SPEC001"
        assert block.microCT_info is None


class TestBlockUpdate:
    def test_all_fields_optional(self):
        update = BlockUpdate()
        assert update.microCT_info is None

    def test_update_microCT_info(self):
        update = BlockUpdate(microCT_info={"resolution": 3.0, "source": "updated"})
        assert update.microCT_info["resolution"] == 3.0


class TestBlockResponse:
    def test_valid_response(self):
        response = BlockResponse(
            block_id="BLOCK001",
            specimen_id="SPEC001",
            microCT_info={"resolution": 1.5},
            created_at=datetime.now(),
        )
        assert response.block_id == "BLOCK001"
        assert response.specimen_id == "SPEC001"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            BlockResponse()
