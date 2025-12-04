import pytest
from pydantic import ValidationError
from temdb.models import (
    AcquisitionFocusScoresResponse,
    BadFocusTileInfo,
    BadFocusTilesResponse,
    TileFocusScore,
)


class TestTileFocusScore:
    def test_valid_tile_focus_score(self):
        score = TileFocusScore(
            tile_id="TILE001",
            raster_index=0,
            focus_score=0.95,
        )
        assert score.tile_id == "TILE001"
        assert score.raster_index == 0
        assert score.focus_score == 0.95

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            TileFocusScore()


class TestAcquisitionFocusScoresResponse:
    def test_valid_response(self):
        response = AcquisitionFocusScoresResponse(
            acquisition_id="ACQ001",
            tile_count=10,
            focus_scores=[
                TileFocusScore(tile_id="TILE001", raster_index=0, focus_score=0.95),
                TileFocusScore(tile_id="TILE002", raster_index=1, focus_score=0.92),
            ],
            mean_focus=0.935,
            median_focus=0.935,
            stddev_focus=0.015,
            min_focus=0.92,
            max_focus=0.95,
        )
        assert response.acquisition_id == "ACQ001"
        assert response.tile_count == 10
        assert len(response.focus_scores) == 2

    def test_empty_focus_scores(self):
        response = AcquisitionFocusScoresResponse(
            acquisition_id="ACQ001",
            tile_count=0,
            focus_scores=[],
        )
        assert response.tile_count == 0
        assert response.mean_focus is None


class TestBadFocusTileInfo:
    def test_valid_bad_focus_tile_info(self):
        info = BadFocusTileInfo(
            tile_id="TILE001",
            acquisition_id="ACQ001",
            raster_index=0,
            focus_score=0.3,
            image_path="/path/to/image.tif",
            stage_position={"x": 100.0, "y": 200.0},
        )
        assert info.tile_id == "TILE001"
        assert info.focus_score == 0.3
        assert info.acquisition_id == "ACQ001"


class TestBadFocusTilesResponse:
    def test_valid_response(self):
        response = BadFocusTilesResponse(
            threshold=0.5,
            count=2,
            tiles=[
                BadFocusTileInfo(
                    tile_id="TILE001",
                    acquisition_id="ACQ001",
                    raster_index=0,
                    focus_score=0.3,
                    image_path="/path/to/image.tif",
                    stage_position={"x": 100.0, "y": 200.0},
                ),
            ],
        )
        assert response.count == 2
        assert response.threshold == 0.5
