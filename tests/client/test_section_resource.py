import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
import requests

from temdb.client.resources.section import SectionResource
from temdb.models import FileObjectRequest, FileObjectResponse, SectionCreate, SectionUpdate
from temdb.models.enums import StorageProtocol

SECTION_URL = "sections/SEC001/images/thumbnail"

API = "http://test/api/v2"
NOW = datetime(2026, 8, 4, tzinfo=timezone.utc)


def _resource():
    request = AsyncMock()
    resource = SectionResource(request, API)
    return resource, request


def _section_payload(**extra) -> dict:
    return {
        "id": 1,
        "section_id": "MEDIA001_S00001",
        "cutting_session_id": "CUT001",
        "block_id": "BLK001",
        "specimen_id": "SPEC001",
        "media_id": "MEDIA001",
        "section_number": 1,
        "timestamp": NOW.isoformat(),
        "condition": "ok",
        **extra,
    }


@pytest.mark.asyncio
async def test_create_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _section_payload(section_id="MEDIA001_S00002", section_number=2)
    out = await res.create(cutting_session_id="CUT001", media_id="MEDIA001", timestamp=NOW, cut_count=7)
    assert request.await_args.kwargs["json"]["cut_count"] == 7
    assert out.section_number == 2


@pytest.mark.asyncio
async def test_create_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(TypeError):
        await res.create(
            SectionCreate(cutting_session_id="CUT001", media_id="MEDIA001", timestamp=NOW),
            cut_count=7,
        )


@pytest.mark.asyncio
async def test_list_by_session_uses_expected_path():
    res, request = _resource()
    request.return_value = [_section_payload(), _section_payload(section_id="MEDIA001_S00002", section_number=2)]
    out = await res.list_by_session("CUT001", limit=2)
    assert request.await_args.args[:2] == ("GET", "sections/sessions/CUT001")
    assert request.await_args.kwargs["params"] == {"skip": 0, "limit": 2}
    assert [s.section_number for s in out] == [1, 2]


@pytest.mark.asyncio
async def test_update_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _section_payload(condition="damaged")
    out = await res.update("MEDIA001_S00001", condition="damaged")
    assert request.await_args.args[:2] == ("PATCH", "sections/MEDIA001_S00001")
    assert request.await_args.kwargs["json"] == {"condition": "damaged"}
    assert out.condition == "damaged"


@pytest.mark.asyncio
async def test_update_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(TypeError):
        await res.update("CUT001", "MEDIA001_S00001", SectionUpdate(condition="ok"), condition_reason="conflict")


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

    result = await resource.put_image_url("SEC001", "thumbnail", location)

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

    await resource.put_image_url("SEC001", "thumbnail")

    request.assert_awaited_once_with("POST", SECTION_URL, json=None)


@pytest.mark.asyncio
async def test_put_image_uploads_bytes_to_presigned_url(monkeypatch):
    resource, _ = _resource()
    file_object = FileObjectResponse.model_validate(_file_object_response())
    put_image_url = AsyncMock(return_value=file_object)
    resource.put_image_url = put_image_url
    uploaded = []

    async def handle(request):
        uploaded.append(await request.aread())
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    monkeypatch.setattr("temdb.client.resources.image.httpx.AsyncClient", lambda: client)

    contents = io.BytesIO(b"section image")
    assert await resource.put_image("SEC001", "thumbnail", contents) is file_object

    put_image_url.assert_awaited_once_with("SEC001", "thumbnail", storage_location=None)
    assert uploaded == [b"section image"]
    assert not contents.closed
    assert client.is_closed


@pytest.mark.asyncio
async def test_put_image_propagates_upload_failure(monkeypatch):
    resource, _ = _resource()
    put_image_url = AsyncMock(return_value=FileObjectResponse.model_validate(_file_object_response()))
    resource.put_image_url = put_image_url
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    monkeypatch.setattr("temdb.client.resources.image.httpx.AsyncClient", lambda: client)

    with pytest.raises(httpx.HTTPStatusError):
        await resource.put_image("SEC001", "thumbnail", io.BytesIO(b"image"))

    put_image_url.assert_awaited_once_with("SEC001", "thumbnail", storage_location=None)


@pytest.mark.asyncio
async def test_get_image_url_adds_expiration_and_returns_model():
    resource, request = _resource()
    request.return_value = _file_object_response()

    result = await resource.get_image_url("SEC001", "thumbnail", expiration=300)

    request.assert_awaited_once_with("GET", SECTION_URL, params={"expiration": 300})
    assert result.expiration == 600


@pytest.mark.asyncio
async def test_get_image_url_omits_expiration_when_unspecified():
    resource, request = _resource()
    request.return_value = _file_object_response()

    await resource.get_image_url("SEC001", "thumbnail")

    request.assert_awaited_once_with("GET", SECTION_URL, params=None)


@pytest.mark.asyncio
async def test_get_image_streams_presigned_response(monkeypatch):
    resource, _ = _resource()
    get_image_url = AsyncMock(return_value=FileObjectResponse.model_validate(_file_object_response()))
    resource.get_image_url = get_image_url
    response = httpx.Response(200, content=b"downloaded section image")
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response))
    monkeypatch.setattr("temdb.client.resources.image.httpx.AsyncClient", lambda: client)

    result = await resource.get_image("SEC001", "thumbnail", expiration=300)

    get_image_url.assert_awaited_once_with("SEC001", "thumbnail", 300)
    assert str(response.request.url) == _file_object_response()["url"]
    assert result == b"downloaded section image"
    assert response.is_closed


@pytest.mark.asyncio
async def test_get_image_closes_response_when_download_fails(monkeypatch):
    resource, _ = _resource()
    resource.get_image_url = AsyncMock(return_value=FileObjectResponse.model_validate(_file_object_response()))
    response = httpx.Response(500)
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response))
    monkeypatch.setattr("temdb.client.resources.image.httpx.AsyncClient", lambda: client)

    with pytest.raises(httpx.HTTPStatusError):
        await resource.get_image("SEC001", "thumbnail")

    assert response.is_closed


@pytest.mark.asyncio
async def test_delete_image_awaits_delete_request():
    resource, request = _resource()

    await resource.delete_image("SEC001", "thumbnail")

    request.assert_awaited_once_with("DELETE", SECTION_URL)


@pytest.mark.asyncio
async def test_delete_image_propagates_request_failure():
    resource, request = _resource()
    request.side_effect = requests.HTTPError("delete failed")

    with pytest.raises(requests.HTTPError, match="delete failed"):
        await resource.delete_image("SEC001", "thumbnail")
