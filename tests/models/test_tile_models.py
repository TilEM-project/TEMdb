import pytest
from pydantic import ValidationError
from temdb.models import Matcher, TileBase, TileCreate, TileResponse


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
            position=0,
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
            tile_id="TILE_001",
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
        assert tile.raster_index == 0
        assert tile.focus_score == 0.95

    def test_tile_create_missing_required_field(self):
        with pytest.raises(ValidationError):
            TileCreate(
                tile_id="TILE_001",
            )

    def test_tile_create_extra_fields_allowed(self):
        tile = TileCreate(
            tile_id="TILE_001",
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
        assert tile.model_extra.get("custom_field") == "extra_data"


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
