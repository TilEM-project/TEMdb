import pytest


@pytest.mark.asyncio
async def test_roi_list(mock_client):
    mock_response = [{"roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001", "section_id": "SECTION001"}]
    mock_client.roi.list.return_value = mock_response

    result = await mock_client.roi.list("SECTION001")
    assert result == mock_response
    mock_client.roi.list.assert_called_once_with("SECTION001")


@pytest.mark.asyncio
async def test_roi_create(mock_client):
    roi_data = {"section_id": "SECTION001", "coordinates": [[0, 0], [100, 100]]}
    mock_response = roi_data.copy()
    mock_response["roi_id"] = "SPEC001.BLK001.SEC001.SUB001.ROI001"
    mock_client.roi.create.return_value = mock_response

    result = await mock_client.roi.create(roi_data)
    assert result == mock_response
    mock_client.roi.create.assert_called_once_with(roi_data)


@pytest.mark.asyncio
async def test_roi_get(mock_client):
    mock_response = {"roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001", "section_id": "SECTION001"}
    mock_client.roi.get.return_value = mock_response

    result = await mock_client.roi.get("SPEC001.BLK001.SEC001.SUB001.ROI001")
    assert result == mock_response
    mock_client.roi.get.assert_called_once_with("SPEC001.BLK001.SEC001.SUB001.ROI001")


@pytest.mark.asyncio
async def test_roi_update(mock_client):
    update_data = {"coordinates": [[0, 0], [200, 200]]}
    mock_response = {
        "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001",
        "section_id": "SECTION001",
        "coordinates": [[0, 0], [200, 200]],
    }
    mock_client.roi.update.return_value = mock_response

    result = await mock_client.roi.update("SPEC001.BLK001.SEC001.SUB001.ROI001", update_data)
    assert result == mock_response
    mock_client.roi.update.assert_called_once_with("SPEC001.BLK001.SEC001.SUB001.ROI001", update_data)


@pytest.mark.asyncio
async def test_roi_delete(mock_client):
    await mock_client.roi.delete("SPEC001.BLK001.SEC001.SUB001.ROI001")
    mock_client.roi.delete.assert_called_once_with("SPEC001.BLK001.SEC001.SUB001.ROI001")
