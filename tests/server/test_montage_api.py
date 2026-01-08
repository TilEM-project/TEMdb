from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from temdb.models import AcquisitionStatus
from temdb.server.documents import (
    AcquisitionDocument,
    AcquisitionTaskDocument,
    ROIDocument,
    SpecimenDocument,
    TileDocument,
)


@pytest.mark.asyncio
async def test_get_tilespec_metadata(
    async_client: AsyncClient, test_acquisition: AcquisitionDocument
):
    """Test retrieving tilespec metadata for a montage."""
    response = await async_client.get(
        f"/api/v2/montages/{test_acquisition.montage_id}/tilespec-metadata"
    )
    assert response.status_code == 200

    data = response.json()
    assert data["montage_id"] == test_acquisition.montage_id
    assert data["width"] == 4096
    assert data["height"] == 4096
    assert data["scope_id"] == "TEST_SCOPE_001"
    assert data["camera_serial"] == "12345"


@pytest.mark.asyncio
async def test_get_tilespec_metadata_not_found(async_client: AsyncClient):
    """Test 404 when montage not found."""
    response = await async_client.get("/api/v2/montages/NONEXISTENT/tilespec-metadata")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_montage_tiles(
    async_client: AsyncClient,
    test_acquisition: AcquisitionDocument,
    test_tile: TileDocument,
):
    """Test retrieving tiles for a montage."""
    response = await async_client.get(
        f"/api/v2/montages/{test_acquisition.montage_id}/tiles"
    )
    assert response.status_code == 200

    data = response.json()
    assert "tiles" in data
    assert "metadata" in data
    assert len(data["tiles"]) == 1
    assert data["tiles"][0]["tile_id"] == test_tile.tile_id


@pytest.mark.asyncio
async def test_get_montage_tiles_pagination(
    async_client: AsyncClient,
    test_acquisition: AcquisitionDocument,
    test_tile: TileDocument,
):
    """Test pagination of montage tiles."""
    response = await async_client.get(
        f"/api/v2/montages/{test_acquisition.montage_id}/tiles",
        params={"limit": 10},
    )
    assert response.status_code == 200

    data = response.json()
    assert "metadata" in data
    assert "next_cursor" in data["metadata"]
    assert "has_more" in data["metadata"]
    assert "returned_count" in data["metadata"]


@pytest.mark.asyncio
async def test_get_montage_tiles_not_found(async_client: AsyncClient):
    """Test 404 when montage not found for tiles."""
    response = await async_client.get("/api/v2/montages/NONEXISTENT/tiles")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_montage_tiles_large_dataset(
    async_client: AsyncClient,
    init_db,
    test_specimen: SpecimenDocument,
    test_roi: ROIDocument,
    test_acquisition_task: AcquisitionTaskDocument,
):
    """Test pagination with a large number of tiles to simulate real montage sizes."""

    acquisition = AcquisitionDocument(
        acquisition_id="TEST_ACQ_LARGE",
        montage_id="TEST_MONTAGE_LARGE",
        specimen_id=test_specimen.specimen_id,
        roi_id=test_roi.roi_id,
        acquisition_task_id=test_acquisition_task.task_id,
        specimen_ref=test_specimen.id,
        roi_ref=test_roi.id,
        acquisition_task_ref=test_acquisition_task.id,
        hardware_settings={
            "scope_id": "TEST_SCOPE_001",
            "camera_model": "Test Camera",
            "camera_serial": "12345",
            "camera_bit_depth": 16,
            "media_type": "tape",
        },
        acquisition_settings={
            "magnification": 1000,
            "spot_size": 2,
            "exposure_time": 100,
            "tile_size": [4096, 4096],
            "tile_overlap": 0.1,
            "saved_bit_depth": 8,
        },
        calibration_info={
            "pixel_size": 4.0,
            "rotation_angle": 1.5,
        },
        tilt_angle=45.0,
        status=AcquisitionStatus.ACQUIRED,
        start_time=datetime.now(timezone.utc),
    )
    await acquisition.insert()

    num_tiles = 250
    tiles = []
    for i in range(num_tiles):
        row = i // 16
        col = i % 16
        tile = TileDocument(
            tile_id=f"TILE_LARGE_{i:04d}",
            acquisition_id=acquisition.acquisition_id,
            acquisition_ref=acquisition.id,
            raster_index=i,
            stage_position={"x": col * 4000.0, "y": row * 4000.0},
            raster_position={"row": row, "col": col},
            focus_score=0.90 + (i % 10) * 0.01,
            min_value=0,
            max_value=255,
            mean_value=128 + (i % 20),
            std_value=25 + (i % 5),
            image_path=f"/path/to/test/tile_{i:04d}.tif",
        )
        tiles.append(tile)

    await TileDocument.insert_many(tiles)

    response = await async_client.get(
        f"/api/v2/montages/{acquisition.montage_id}/tilespec-metadata"
    )
    assert response.status_code == 200
    metadata = response.json()
    assert metadata["montage_id"] == acquisition.montage_id
    assert metadata["tilt_angle"] == 45.0
    assert metadata["pixel_size"] == 4.0
    assert metadata["rotation_angle"] == 1.5

    page_size = 100
    response = await async_client.get(
        f"/api/v2/montages/{acquisition.montage_id}/tiles",
        params={"limit": page_size},
    )
    assert response.status_code == 200
    data = response.json()

    assert len(data["tiles"]) == page_size
    assert data["metadata"]["returned_count"] == page_size
    assert data["metadata"]["has_more"] is True
    first_cursor = data["metadata"]["next_cursor"]

    for i, tile in enumerate(data["tiles"]):
        assert tile["raster_index"] == i

    all_tiles = data["tiles"]
    cursor = first_cursor
    pages_fetched = 1

    while data["metadata"]["has_more"]:
        response = await async_client.get(
            f"/api/v2/montages/{acquisition.montage_id}/tiles",
            params={"cursor": cursor, "limit": page_size},
        )
        assert response.status_code == 200
        data = response.json()
        all_tiles.extend(data["tiles"])
        cursor = data["metadata"]["next_cursor"]
        pages_fetched += 1

        assert pages_fetched <= 10, "Too many pages fetched"

    assert len(all_tiles) == num_tiles
    expected_pages = (num_tiles + page_size - 1) // page_size
    assert pages_fetched == expected_pages

    for i, tile in enumerate(all_tiles):
        assert tile["raster_index"] == i
        assert tile["tile_id"] == f"TILE_LARGE_{i:04d}"

    sample_tile = all_tiles[42]
    assert "acquisition_id" in sample_tile
    assert "image_path" in sample_tile
    assert "stage_position" in sample_tile
    assert "raster_position" in sample_tile
    assert "focus_score" in sample_tile
    assert "mean_value" in sample_tile
    assert "std_value" in sample_tile
