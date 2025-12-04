import pytest


@pytest.mark.asyncio
async def test_acquisition_list(mock_client):
    mock_client.acquisition.list.return_value = [{"acquisition_id": "ACQ001"}]
    result = await mock_client.acquisition.list()
    assert result == [{"acquisition_id": "ACQ001"}]
    mock_client.acquisition.list.assert_called_once()


@pytest.mark.asyncio
async def test_acquisition_create(mock_client):
    acquisition_data = {"acquisition_id": "ACQ002", "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001"}
    mock_client.acquisition.create.return_value = acquisition_data
    result = await mock_client.acquisition.create(acquisition_data)
    assert result == acquisition_data
    mock_client.acquisition.create.assert_called_once_with(acquisition_data)


@pytest.mark.asyncio
async def test_acquisition_get(mock_client):
    acquisition_data = {"acquisition_id": "ACQ002", "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001"}

    mock_client.acquisition.get.return_value = acquisition_data
    result = await mock_client.acquisition.get("ACQ002")
    assert result == acquisition_data
    mock_client.acquisition.get.assert_called_once_with("ACQ002")


@pytest.mark.asyncio
async def test_acquisition_update(mock_client):
    acquisition_data = {"acquisition_id": "ACQ002", "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001"}

    update_data = {"status": "COMPLETED"}
    mock_client.acquisition.update.return_value = {**acquisition_data, **update_data}
    result = await mock_client.acquisition.update("ACQ002", update_data)
    assert result == {**acquisition_data, **update_data}
    mock_client.acquisition.update.assert_called_once_with("ACQ002", update_data)


@pytest.mark.asyncio
async def test_acquisition_delete(mock_client):
    await mock_client.acquisition.delete("ACQ002")
    mock_client.acquisition.delete.assert_called_once_with("ACQ002")


@pytest.mark.asyncio
async def test_acquisition_get_with_full_metadata(mock_client):
    metadata_response = {
        "acquisition": {
            "acquisition_id": "ACQ002",
            "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001",
        },
        "task": {"task_id": "TASK001", "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001"},
        "roi": {"roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001", "section_id": "SEC001"},
        "section": {"section_id": "SEC001", "specimen_id": "SPEC001"},
        "specimen": {"specimen_id": "SPEC001", "name": "Test Specimen"},
        "tiles": [
            {
                "tile_id": "TILE003",
                "acquisition_id": "ACQ002",
                "raster_index": 0,
                "stage_position": {"x": 0.0, "y": 0.0, "z": 0.0},
                "raster_position": {"row": 0, "col": 0},
                "focus_score": 0.85,
                "min_value": 10.5,
                "max_value": 255.0,
                "mean_value": 128.7,
                "std_value": 45.2,
                "image_path": "/data/tiles/TILE003.tiff",
                "created_at": "2025-05-30T10:00:00Z",
                "updated_at": "2025-05-30T10:00:00Z",
                "version": 1,
            }
        ],
    }
    mock_client.acquisition.get_with_full_metadata.return_value = metadata_response

    result = await mock_client.acquisition.get_with_full_metadata("ACQ002")
    assert result == metadata_response
    mock_client.acquisition.get_with_full_metadata.assert_called_once_with("ACQ002")


@pytest.mark.asyncio
async def test_acquisition_list_with_full_metadata(mock_client):
    metadata_response = {
        "acquisitions": [
            {
                "acquisition": {
                    "acquisition_id": "ACQ001",
                    "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001",
                },
                "task": {"task_id": "TASK001", "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001"},
                "roi": {"roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001", "section_id": "SEC001"},
                "section": {"section_id": "SEC001", "specimen_id": "SPEC001"},
                "specimen": {"specimen_id": "SPEC001", "name": "Test Specimen"},
                "tiles": [
                    {
                        "tile_id": "TILE001",
                        "acquisition_id": "ACQ001",
                        "raster_index": 0,
                        "stage_position": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "raster_position": {"row": 0, "col": 0},
                        "focus_score": 0.92,
                        "min_value": 8.2,
                        "max_value": 250.0,
                        "mean_value": 135.4,
                        "std_value": 42.8,
                        "image_path": "/data/tiles/TILE001.tiff",
                        "created_at": "2025-05-30T09:30:00Z",
                        "updated_at": "2025-05-30T09:30:00Z",
                        "version": 1,
                    },
                    {
                        "tile_id": "TILE002",
                        "acquisition_id": "ACQ001",
                        "raster_index": 1,
                        "stage_position": {"x": 512.0, "y": 0.0, "z": 0.0},
                        "raster_position": {"row": 0, "col": 1},
                        "focus_score": 0.88,
                        "min_value": 12.1,
                        "max_value": 248.5,
                        "mean_value": 142.3,
                        "std_value": 38.9,
                        "image_path": "/data/tiles/TILE002.tiff",
                        "created_at": "2025-05-30T09:32:00Z",
                        "updated_at": "2025-05-30T09:32:00Z",
                        "version": 1,
                    },
                ],
            }
        ],
        "metadata": {"total": 1, "limit": 50, "cursor": None},
    }
    mock_client.acquisition.list_with_full_metadata.return_value = metadata_response

    result = await mock_client.acquisition.list_with_full_metadata(limit=50)
    assert result == metadata_response
    mock_client.acquisition.list_with_full_metadata.assert_called_once_with(limit=50)
