import io
from unittest.mock import AsyncMock, Mock

import pytest
import requests

from temdb.client.resources.acquisition import AcquisitionResource
from temdb.models import FileObjectRequest, FileObjectResponse


@pytest.fixture
def image_resource():
    request = AsyncMock()
    return AcquisitionResource(request, "http://api.example.com/api/v2"), request


def _image_response():
    return {
        "protocol": "s3",
        "server": "http://minio.example.com",
        "bucket": "tiles",
        "key": "tiles/tile.tif",
        "url": "http://minio.example.com/tiles/tiles/tile.tif?signature=test",
        "expiration": 600,
    }


@pytest.mark.parametrize("with_location", [False, True])
async def test_tile_put_image_url_uses_api_put_route(image_resource, with_location):
    resource, request = image_resource
    request.return_value = _image_response()
    location = (
        FileObjectRequest(
            protocol="s3",
            server="http://minio.example.com",
            bucket="tiles",
            key="/tiles/tile.tif",
            expiration=600,
        )
        if with_location
        else None
    )

    result = await resource.put_image_url("ACQ001", "tile", location)

    request.assert_awaited_once_with(
        "POST",
        "acquisitions/ACQ001/tiles/tile/image",
        json=location.model_dump(exclude_unset=True) if location else None,
    )
    assert result == FileObjectResponse.model_validate(_image_response())


@pytest.mark.parametrize("expiration", [None, 300])
async def test_tile_get_image_url(image_resource, expiration):
    resource, request = image_resource
    request.return_value = _image_response()

    result = await resource.get_image_url("ACQ001", "tile", expiration=expiration)

    request.assert_awaited_once_with(
        "GET",
        "acquisitions/ACQ001/tiles/tile/image",
        params={"expiration": expiration} if expiration is not None else None,
    )
    assert result == FileObjectResponse.model_validate(_image_response())


@pytest.mark.parametrize("operation", ["put", "get"])
@pytest.mark.parametrize("tile_ids", [None, ["tile"]])
async def test_tile_bulk_image_urls_use_json_body_and_return_mapping(image_resource, operation, tile_ids):
    resource, request = image_resource
    request.return_value = {"tile": _image_response()}
    method = getattr(resource, f"{operation}_image_urls")

    result = await method("ACQ001", tile_ids=tile_ids, expiration=300)

    request.assert_awaited_once_with(
        "POST" if operation == "put" else "GET",
        "acquisitions/ACQ001/tiles/images",
        json=tile_ids,
        params={"expiration": 300},
    )
    assert result == {"tile": FileObjectResponse.model_validate(_image_response())}


@pytest.mark.parametrize("upload_fails", [False, True])
async def test_tile_put_image_uploads_and_propagates_errors(image_resource, monkeypatch, upload_fails):
    resource, _ = image_resource
    file_object = FileObjectResponse.model_validate(_image_response())
    resource.put_image_url = AsyncMock(return_value=file_object)
    upload_response = Mock()
    if upload_fails:
        upload_response.raise_for_status.side_effect = requests.HTTPError("upload failed")
    file_session = Mock()
    file_session.put.return_value = upload_response
    monkeypatch.setattr("requests.Session.put", file_session.put)
    contents = io.BytesIO(b"tile image")

    if upload_fails:
        with pytest.raises(requests.HTTPError, match="upload failed"):
            await resource.put_image("ACQ001", "tile", contents)
    else:
        assert await resource.put_image("ACQ001", "tile", contents) is file_object

    resource.put_image_url.assert_awaited_once_with("ACQ001", "tile", None)
    file_session.put.assert_called_once_with(file_object.url, data=contents)
    upload_response.raise_for_status.assert_called_once_with()


async def test_tile_delete_image(image_resource):
    resource, request = image_resource

    await resource.delete_image("ACQ001", "tile")

    request.assert_awaited_once_with("DELETE", "acquisitions/ACQ001/tiles/tile/image")


@pytest.mark.parametrize("tile_ids", [None, ["tile"]])
async def test_tile_delete_images_awaits_request_and_returns_deleted_ids(image_resource, tile_ids):
    resource, request = image_resource
    request.return_value = ["tile"]

    result = await resource.delete_images("ACQ001", tile_ids=tile_ids)

    request.assert_awaited_once_with("DELETE", "acquisitions/ACQ001/tiles/images", json=tile_ids)
    assert result == ["tile"]


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
                "image": {
                    "protocol": "s3",
                    "server": "http://localhost:9000",
                    "bucket": "tiles",
                    "key": "TILE003.tiff",
                },
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
                        "image": {
                            "protocol": "s3",
                            "server": "http://localhost:9000",
                            "bucket": "tiles",
                            "key": "TILE001.tiff",
                        },
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
                        "image": {
                            "protocol": "s3",
                            "server": "http://localhost:9000",
                            "bucket": "tiles",
                            "key": "TILE002.tiff",
                        },
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
