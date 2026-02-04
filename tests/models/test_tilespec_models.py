import pytest
from pydantic import ValidationError

from temdb.models import LensCorrectionModel, PaginatedTileResponse, TileResponse, TileSpecMetadata


class TestTileSpecMetadata:
    def test_tilespec_metadata_required_fields(self):
        with pytest.raises(ValidationError):
            TileSpecMetadata()

    def test_tilespec_metadata_creation(self):
        metadata = TileSpecMetadata(
            montage_id="MONTAGE_001",
            width=4096,
            height=4096,
            saved_bit_depth=8,
            pixel_size=4.0,
            rotation_angle=0.0,
            lens_model=None,
            scope_id="SCOPE_001",
            camera_serial="CAM_12345",
            section_id="SECTION_001",
            section_number=1,
            media_id="MEDIA_001",
            roi_id="ROI_001",
            specimen_id="SPECIMEN_001",
            storage_base_path="/data/images",
        )
        assert metadata.montage_id == "MONTAGE_001"
        assert metadata.width == 4096
        assert metadata.height == 4096
        assert metadata.saved_bit_depth == 8

    def test_tilespec_metadata_with_lens_model(self):
        lens = LensCorrectionModel(
            id=1,
            type="leaf",
            class_name="mpicbg.trakem2.transform.NonLinearCoordinateTransform",
            data_string="some_data_string",
        )
        metadata = TileSpecMetadata(
            montage_id="MONTAGE_001",
            width=4096,
            height=4096,
            saved_bit_depth=8,
            pixel_size=4.0,
            rotation_angle=0.0,
            lens_model=lens,
            scope_id="SCOPE_001",
            camera_serial="CAM_12345",
            section_id="SECTION_001",
            section_number=1,
            media_id="MEDIA_001",
            roi_id="ROI_001",
            specimen_id="SPECIMEN_001",
            storage_base_path=None,
        )
        assert metadata.lens_model is not None
        assert metadata.lens_model.id == 1


class TestPaginatedTileResponse:
    def test_paginated_response(self):
        tile = TileResponse(
            tile_id="TILE_001",
            acquisition_id="ACQ_001",
            image_path="/path/to/image.tif",
            raster_position={"row": 0, "col": 0},
            stage_position={"x": 1000.0, "y": 2000.0},
            raster_index=0,
            focus_score=0.95,
            min_value=0.0,
            max_value=255.0,
            mean_value=128.0,
            std_value=30.0,
        )
        response = PaginatedTileResponse(
            tiles=[tile],
            metadata={"next_cursor": 1, "has_more": False, "returned_count": 1},
        )
        assert len(response.tiles) == 1
        assert response.metadata["has_more"] is False
