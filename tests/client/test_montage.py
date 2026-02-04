from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.montage import MontageResource
from temdb.client.resources.sync_wrappers.montage import SyncMontageResourceWrapper
from temdb.models import AsyncTileSpecData, PaginatedTileResponse, TileSpecData, TileSpecMetadata


@pytest.fixture
def mock_request():
    return AsyncMock()


@pytest.fixture
def montage_resource(mock_request):
    return MontageResource(mock_request, "http://test/api/v2")


@pytest.mark.asyncio
async def test_get_tilespec_metadata(montage_resource, mock_request):
    """Test fetching tilespec metadata."""
    mock_request.return_value = {
        "montage_id": "MONTAGE_001",
        "width": 4096,
        "height": 4096,
        "saved_bit_depth": 8,
        "pixel_size": 4.0,
        "rotation_angle": 0.0,
        "lens_model": None,
        "scope_id": "SCOPE_001",
        "camera_serial": "CAM_123",
        "section_id": "SEC_001",
        "section_number": 1,
        "media_id": "MEDIA_001",
        "roi_id": "ROI_001",
        "specimen_id": "SPEC_001",
        "storage_base_path": "/data",
        "tilt_angle": 45.0,
    }

    result = await montage_resource.get_tilespec_metadata("MONTAGE_001")

    assert isinstance(result, TileSpecMetadata)
    assert result.montage_id == "MONTAGE_001"
    assert result.width == 4096
    mock_request.assert_called_once_with("GET", "montages/MONTAGE_001/tilespec-metadata")


@pytest.mark.asyncio
async def test_get_tiles_page(montage_resource, mock_request):
    """Test fetching a page of tiles."""
    mock_request.return_value = {
        "tiles": [
            {
                "tile_id": "TILE_001",
                "acquisition_id": "ACQ_001",
                "image_path": "/path/to/img.tif",
                "raster_position": {"row": 0, "col": 0},
                "stage_position": {"x": 100.0, "y": 200.0},
                "raster_index": 0,
                "focus_score": 0.95,
                "min_value": 0.0,
                "max_value": 255.0,
                "mean_value": 128.0,
                "std_value": 30.0,
            }
        ],
        "metadata": {"next_cursor": 0, "has_more": False, "returned_count": 1},
    }

    result = await montage_resource.get_tiles_page("MONTAGE_001", cursor=None, limit=1000)

    assert isinstance(result, PaginatedTileResponse)
    assert len(result.tiles) == 1
    assert result.tiles[0].tile_id == "TILE_001"


@pytest.mark.asyncio
async def test_iter_tiles(montage_resource, mock_request):
    """Test iterating over all tiles."""
    mock_request.side_effect = [
        {
            "tiles": [
                {
                    "tile_id": "TILE_001",
                    "acquisition_id": "ACQ_001",
                    "image_path": "/path/1.tif",
                    "raster_position": {"row": 0, "col": 0},
                    "stage_position": {"x": 100.0, "y": 200.0},
                    "raster_index": 0,
                    "focus_score": 0.95,
                    "min_value": 0.0,
                    "max_value": 255.0,
                    "mean_value": 128.0,
                    "std_value": 30.0,
                }
            ],
            "metadata": {"next_cursor": 0, "has_more": True, "returned_count": 1},
        },
        {
            "tiles": [
                {
                    "tile_id": "TILE_002",
                    "acquisition_id": "ACQ_001",
                    "image_path": "/path/2.tif",
                    "raster_position": {"row": 0, "col": 1},
                    "stage_position": {"x": 200.0, "y": 200.0},
                    "raster_index": 1,
                    "focus_score": 0.90,
                    "min_value": 0.0,
                    "max_value": 255.0,
                    "mean_value": 130.0,
                    "std_value": 32.0,
                }
            ],
            "metadata": {"next_cursor": 1, "has_more": False, "returned_count": 1},
        },
    ]

    tiles = []
    async for tile in montage_resource.iter_tiles("MONTAGE_001", batch_size=1):
        tiles.append(tile)

    assert len(tiles) == 2
    assert tiles[0].tile_id == "TILE_001"
    assert tiles[1].tile_id == "TILE_002"


@pytest.mark.asyncio
async def test_get_tilespec_data(montage_resource, mock_request):
    """Test getting combined metadata and tiles."""
    mock_request.side_effect = [
        # First call: metadata
        {
            "montage_id": "MONTAGE_001",
            "width": 4096,
            "height": 4096,
            "saved_bit_depth": 8,
            "pixel_size": 4.0,
            "rotation_angle": 0.0,
            "lens_model": None,
            "scope_id": "SCOPE_001",
            "camera_serial": "CAM_123",
            "section_id": "SEC_001",
            "section_number": 1,
            "media_id": "MEDIA_001",
            "roi_id": "ROI_001",
            "specimen_id": "SPEC_001",
            "storage_base_path": "/data",
            "tilt_angle": None,
        },
        # Second call: tiles
        {
            "tiles": [
                {
                    "tile_id": "TILE_001",
                    "acquisition_id": "ACQ_001",
                    "image_path": "/path/1.tif",
                    "raster_position": {"row": 0, "col": 0},
                    "stage_position": {"x": 100.0, "y": 200.0},
                    "raster_index": 0,
                    "focus_score": 0.95,
                    "min_value": 0.0,
                    "max_value": 255.0,
                    "mean_value": 128.0,
                    "std_value": 30.0,
                }
            ],
            "metadata": {"next_cursor": 0, "has_more": False, "returned_count": 1},
        },
    ]

    result = await montage_resource.get_tilespec_data("MONTAGE_001")

    assert isinstance(result, AsyncTileSpecData)
    assert result.metadata.montage_id == "MONTAGE_001"
    assert result.metadata.width == 4096

    # Iterate through tiles
    tiles = []
    async for tile in result.tiles:
        tiles.append(tile)

    assert len(tiles) == 1
    assert tiles[0].tile_id == "TILE_001"


class TestSyncMontageResourceWrapper:
    def test_get_tilespec_metadata_sync(self, montage_resource, mock_request):
        """Test sync wrapper for metadata."""
        mock_request.return_value = {
            "montage_id": "MONTAGE_001",
            "width": 4096,
            "height": 4096,
            "saved_bit_depth": 8,
            "pixel_size": 4.0,
            "rotation_angle": 0.0,
            "lens_model": None,
            "scope_id": "SCOPE_001",
            "camera_serial": "CAM_123",
            "section_id": "SEC_001",
            "section_number": 1,
            "media_id": "MEDIA_001",
            "roi_id": "ROI_001",
            "specimen_id": "SPEC_001",
            "storage_base_path": "/data",
            "tilt_angle": 45.0,
        }

        sync_wrapper = SyncMontageResourceWrapper(montage_resource)
        result = sync_wrapper.get_tilespec_metadata("MONTAGE_001")

        assert isinstance(result, TileSpecMetadata)
        assert result.montage_id == "MONTAGE_001"

    def test_iter_tiles_sync(self, montage_resource, mock_request):
        """Test sync wrapper for tile iteration."""
        mock_request.return_value = {
            "tiles": [
                {
                    "tile_id": "TILE_001",
                    "acquisition_id": "ACQ_001",
                    "image_path": "/path/to/img.tif",
                    "raster_position": {"row": 0, "col": 0},
                    "stage_position": {"x": 100.0, "y": 200.0},
                    "raster_index": 0,
                    "focus_score": 0.95,
                    "min_value": 0.0,
                    "max_value": 255.0,
                    "mean_value": 128.0,
                    "std_value": 30.0,
                }
            ],
            "metadata": {"next_cursor": 0, "has_more": False, "returned_count": 1},
        }

        sync_wrapper = SyncMontageResourceWrapper(montage_resource)
        tiles = list(sync_wrapper.iter_tiles("MONTAGE_001"))

        assert len(tiles) == 1
        assert tiles[0].tile_id == "TILE_001"

    def test_get_tilespec_data_sync(self, montage_resource, mock_request):
        """Test sync wrapper for combined metadata and tiles."""
        mock_request.side_effect = [
            # First call: metadata
            {
                "montage_id": "MONTAGE_001",
                "width": 4096,
                "height": 4096,
                "saved_bit_depth": 8,
                "pixel_size": 4.0,
                "rotation_angle": 0.0,
                "lens_model": None,
                "scope_id": "SCOPE_001",
                "camera_serial": "CAM_123",
                "section_id": "SEC_001",
                "section_number": 1,
                "media_id": "MEDIA_001",
                "roi_id": "ROI_001",
                "specimen_id": "SPEC_001",
                "storage_base_path": "/data",
                "tilt_angle": None,
            },
            # Second call: tiles
            {
                "tiles": [
                    {
                        "tile_id": "TILE_001",
                        "acquisition_id": "ACQ_001",
                        "image_path": "/path/1.tif",
                        "raster_position": {"row": 0, "col": 0},
                        "stage_position": {"x": 100.0, "y": 200.0},
                        "raster_index": 0,
                        "focus_score": 0.95,
                        "min_value": 0.0,
                        "max_value": 255.0,
                        "mean_value": 128.0,
                        "std_value": 30.0,
                    }
                ],
                "metadata": {"next_cursor": 0, "has_more": False, "returned_count": 1},
            },
        ]

        sync_wrapper = SyncMontageResourceWrapper(montage_resource)
        result = sync_wrapper.get_tilespec_data("MONTAGE_001")

        assert isinstance(result, TileSpecData)
        assert result.metadata.montage_id == "MONTAGE_001"
        assert result.metadata.width == 4096

        # Iterate through tiles
        tiles = list(result.tiles)
        assert len(tiles) == 1
        assert tiles[0].tile_id == "TILE_001"
