import io
from unittest.mock import AsyncMock, Mock

import pytest
import requests

from temdb.client.resources.section import SectionResource
from temdb.models import FileObjectRequest, FileObjectResponse
from temdb.models.enums import StorageProtocol

SECTION_URL = "sections/sessions/CUT001/sections/SEC001/image"


def _file_object_response(**overrides):
    return {
        "protocol": "s3",
        "server": "http://minio.example.com",
        "bucket": "section-images",
        "key": "sections/SEC001.png",
        "url": "http://minio.example.com/section-images/sections/SEC001.png?signature=test",
        "expiration": 600,
        **overrides,
    }


def _resource():
    request = AsyncMock()
    resource = SectionResource(request, "http://api.example.com/api/v2")
    resource._file_session = Mock()
    return resource, request


@pytest.mark.asyncio
async def test_put_image_url_posts_optional_storage_location_and_returns_model():
    resource, request = _resource()
    request.return_value = _file_object_response()
    location = FileObjectRequest(
        protocol=StorageProtocol.S3,
        server="http://minio.example.com",
        bucket="section-images",
        key="/sections/SEC001.png",
        expiration=600,
    )

    result = await resource.put_image_url("CUT001", "SEC001", location)

    request.assert_awaited_once_with(
        "POST",
        SECTION_URL,
        json={
            "protocol": StorageProtocol.S3,
            "server": "http://minio.example.com",
            "bucket": "section-images",
            "key": "/sections/SEC001.png",
            "expiration": 600,
        },
    )
    assert result.key == "sections/SEC001.png"
    assert result.expiration == 600


@pytest.mark.asyncio
async def test_put_image_url_without_location_posts_none():
    resource, request = _resource()
    request.return_value = _file_object_response()

    await resource.put_image_url("CUT001", "SEC001")

    request.assert_awaited_once_with("POST", SECTION_URL, json=None)


@pytest.mark.asyncio
async def test_put_image_uploads_bytes_to_presigned_url():
    resource, _ = _resource()
    file_object = FileObjectResponse.model_validate(_file_object_response())
    put_image_url = AsyncMock(return_value=file_object)
    resource.put_image_url = put_image_url
    contents = io.BytesIO(b"section image")
    upload_response = Mock()
    resource._file_session.put.return_value = upload_response

    result = await resource.put_image("CUT001", "SEC001", contents)

    put_image_url.assert_awaited_once_with("CUT001", "SEC001", None)
    resource._file_session.put.assert_called_once_with(result.url, data=contents)
    upload_response.raise_for_status.assert_called_once_with()
    assert result is file_object


@pytest.mark.asyncio
async def test_put_image_propagates_upload_failure():
    resource, _ = _resource()
    put_image_url = AsyncMock(
        return_value=FileObjectResponse.model_validate(_file_object_response())
    )
    resource.put_image_url = put_image_url
    upload_response = Mock()
    upload_response.raise_for_status.side_effect = requests.HTTPError("upload failed")
    resource._file_session.put.return_value = upload_response

    with pytest.raises(requests.HTTPError, match="upload failed"):
        await resource.put_image("CUT001", "SEC001", io.BytesIO(b"image"))

    put_image_url.assert_awaited_once_with("CUT001", "SEC001", None)


@pytest.mark.asyncio
async def test_get_image_url_adds_expiration_and_returns_model():
    resource, request = _resource()
    request.return_value = _file_object_response()

    result = await resource.get_image_url("CUT001", "SEC001", expiration=300)

    request.assert_awaited_once_with("GET", SECTION_URL, params={"expiration": 300})
    assert result.expiration == 600


@pytest.mark.asyncio
async def test_get_image_url_omits_expiration_when_unspecified():
    resource, request = _resource()
    request.return_value = _file_object_response()

    await resource.get_image_url("CUT001", "SEC001")

    request.assert_awaited_once_with("GET", SECTION_URL, params=None)


@pytest.mark.asyncio
async def test_get_image_streams_presigned_response():
    resource, _ = _resource()
    get_image_url = AsyncMock(return_value=FileObjectResponse.model_validate(_file_object_response()))
    resource.get_image_url = get_image_url
    response = Mock()
    response.raw = io.BytesIO(b"downloaded section image")
    resource._file_session.get.return_value = response

    result = await resource.get_image("CUT001", "SEC001", expiration=300)

    get_image_url.assert_awaited_once_with("CUT001", "SEC001", 300)
    resource._file_session.get.assert_called_once_with(
        "http://minio.example.com/section-images/sections/SEC001.png?signature=test",
        stream=True,
    )
    response.raise_for_status.assert_called_once_with()
    assert isinstance(result, io.BufferedReader)
    assert result.read() == b"downloaded section image"
    result.close()


@pytest.mark.asyncio
async def test_get_image_closes_response_when_download_fails():
    resource, _ = _resource()
    resource.get_image_url = AsyncMock(
        return_value=FileObjectResponse.model_validate(_file_object_response())
    )
    response = Mock()
    response.raw = io.BytesIO(b"")
    response.raise_for_status.side_effect = requests.HTTPError("download failed")
    resource._file_session.get.return_value = response

    with pytest.raises(requests.HTTPError, match="download failed"):
        await resource.get_image("CUT001", "SEC001")

    response.close.assert_called_once_with()
