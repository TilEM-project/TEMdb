import uuid

import pytest
from pydantic import ValidationError

from temdb.models import Matcher, TileBase, TileCreate, TileResponse

TILE_UUID = uuid.UUID("0190a6b2-7c3e-7000-8000-000000000001")


class TestMatcher:
    def test_valid_matcher(self):
        matcher = Matcher(
            row=0,
            col=1,
            dX=5.0,
            dY=3.0,
            dXsd=0.1,
            dYsd=0.1,
            distance=5.83,
            rotation=0.5,
            match_quality=0.95,
            position="top",
            pX=[100.0, 200.0],
            pY=[100.0, 200.0],
            qX=[105.0, 205.0],
            qY=[103.0, 203.0],
        )
        assert matcher.row == 0
        assert matcher.col == 1
        assert matcher.match_quality == 0.95


class TestTileCreate:
    def test_valid_tile_create(self):
        tile = TileCreate(
            tile_id=str(TILE_UUID),
            raster_index=0,
            stage_position={"x": 100.0, "y": 200.0},
            raster_position={"row": 0, "col": 0},
            focus_score=0.95,
            min_value=0.0,
            max_value=255.0,
            mean_value=128.0,
            std_value=25.0,
            image_path="/data/tiles/TILE_001.tif",
        )
        assert tile.tile_id == TILE_UUID
        assert tile.raster_index == 0
        assert tile.focus_score == 0.95

    def test_tile_create_missing_required_field(self):
        with pytest.raises(ValidationError):
            TileCreate(
                tile_id=str(TILE_UUID),
            )

    def test_tile_create_non_uuid_tile_id_rejected(self):
        with pytest.raises(ValidationError):
            TileCreate(
                tile_id="TILE_OLD_STYLE_123",
                raster_index=0,
                stage_position={"x": 100.0, "y": 200.0},
                raster_position={"row": 0, "col": 0},
                focus_score=0.95,
                min_value=0.0,
                max_value=255.0,
                mean_value=128.0,
                std_value=25.0,
                image_path="/data/tiles/TILE_001.tif",
            )

    def test_tile_create_tile_id_optional(self):
        tile = TileCreate(
            raster_index=0,
            stage_position={"x": 100.0, "y": 200.0},
            raster_position={"row": 0, "col": 0},
            focus_score=0.95,
            min_value=0.0,
            max_value=255.0,
            mean_value=128.0,
            std_value=25.0,
            image_path="/data/tiles/TILE_001.tif",
        )
        assert tile.tile_id is None

    def test_tile_create_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            TileCreate(
                tile_id=str(TILE_UUID),
                raster_index=0,
                stage_position={"x": 100.0, "y": 200.0},
                raster_position={"row": 0, "col": 0},
                focus_score=0.95,
                min_value=0.0,
                max_value=255.0,
                mean_value=128.0,
                std_value=25.0,
                image_path="/data/tiles/TILE_001.tif",
                custom_field="extra_data",
            )


class TestTileResponse:
    def test_valid_tile_response(self):
        tile = TileResponse(
            tile_id="TILE_001",
            acquisition_id="ACQ_001",
            raster_index=0,
            stage_position={"x": 100.0, "y": 200.0},
            raster_position={"row": 0, "col": 0},
            focus_score=0.95,
            min_value=0.0,
            max_value=255.0,
            mean_value=128.0,
            std_value=25.0,
            image_path="/data/tiles/TILE_001.tif",
        )
        assert tile.tile_id == "TILE_001"
        assert tile.acquisition_id == "ACQ_001"


class TestTileBase:
    def test_tile_base_all_optional(self):
        tile = TileBase()
        assert tile.stage_position is None
        assert tile.focus_score is None

    def test_tile_base_with_values(self):
        tile = TileBase(
            focus_score=0.9,
            image_path="/path/to/image.tif",
        )
        assert tile.focus_score == 0.9
        assert tile.image_path == "/path/to/image.tif"

    def test_tile_base_with_stage_and_raster_positions(self):
        tile = TileBase(
            stage_position={"x": 100, "y": 200},
            raster_position={"row": 1, "col": 2},
        )
        assert tile.stage_position is not None
        assert tile.raster_position is not None
        assert tile.stage_position.x == 100
        assert tile.stage_position.y == 200
        assert tile.raster_position.row == 1
        assert tile.raster_position.col == 2

    def test_tile_base_stage_position_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            TileBase(stage_position={"x": 100, "y": 200, "z": 300})
