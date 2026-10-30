import io
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from temdb.client.resources.acquisition import (
    AcquisitionResource,
    DeletedImagePage,
    DeletedImages,
    ImagePageMetadata,
    ImageURLPage,
    ImageURLs,
)
from temdb.models import AcquisitionCreate, AcquisitionUpdate, FileObjectRequest, FileObjectResponse

API = "http://test/api/v2"
NOW = datetime(2026, 8, 4, tzinfo=timezone.utc)
MICROSCOPE_ID = "TEM-01"


def _page_metadata(**fields) -> dict:
    return {
        "returned_count": 1,
        "limit": 100,
        "current_cursor": None,
        "next_cursor": None,
        "has_more": False,
        "errors": {},
        **fields,
    }


def _resource():
    request = AsyncMock()
    return AcquisitionResource(request, API), request


def _hardware_settings() -> dict:
    return {
        "camera_model": "cam-x",
        "camera_serial": "123",
        "camera_bit_depth": 16,
        "media_type": "wafer",
    }


def _acquisition_settings() -> dict:
    return {
        "magnification": 20000,
        "spot_size": 2,
        "exposure_time": 150,
        "tile_size": [4096, 4096],
        "tile_overlap": 0.1,
        "saved_bit_depth": 8,
    }


def _acquisition_payload(**extra) -> dict:
    return {
        "id": 1,
        "acquisition_id": "ACQ001",
        "run_id": str(uuid4()),
        "montage_id": "MONT001",
        "specimen_id": "SPEC001",
        "roi_id": "SPEC001.BLK001.SEC001.SUB001.ROI001",
        "acquisition_task_id": "TASK001",
        "microscope_id": MICROSCOPE_ID,
        "dataset_id": None,
        "kind": "montage",
        "lc_id": None,
        "hardware_settings": _hardware_settings(),
        "acquisition_settings": _acquisition_settings(),
        "qc_state": "pending",
        "transfer_state": "not_started",
        "start_time": NOW.isoformat(),
        **extra,
    }


def _tile_payload(**extra) -> dict:
    return {
        "tile_id": "M001_r000_c000",
        "acquisition_id": "ACQ001",
        "raster_index": 0,
        "stage_position": {"x": 0.0, "y": 0.0},
        "raster_position": {"row": 0, "col": 0},
        "retake": 0,
        "focus_score": 0.95,
        "min_value": 5.0,
        "max_value": 255.0,
        "mean_value": 120.0,
        "std_value": 15.0,
        "image": {
            "protocol": "s3",
            "server": "http://localhost:9000",
            "bucket": "images",
            "key": "s3://bucket/tile-0.tiff",
        },
        **extra,
    }


@pytest.mark.asyncio
async def test_create_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _acquisition_payload(acquisition_id="ACQ002")
    out = await res.create(
        acquisition_id="ACQ002",
        montage_id="MONT002",
        acquisition_task_id="TASK002",
        microscope_id=MICROSCOPE_ID,
        hardware_settings=_hardware_settings(),
        acquisition_settings=_acquisition_settings(),
    )
    assert request.await_args.args[:2] == ("POST", "acquisitions")
    assert request.await_args.kwargs["json"]["acquisition_id"] == "ACQ002"
    assert out.acquisition_id == "ACQ002"


@pytest.mark.asyncio
async def test_create_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(TypeError):
        await res.create(
            AcquisitionCreate(
                acquisition_id="ACQ001",
                montage_id="MONT001",
                acquisition_task_id="TASK001",
                microscope_id=MICROSCOPE_ID,
                hardware_settings=_hardware_settings(),
                acquisition_settings=_acquisition_settings(),
            ),
            montage_set_name="conflict",
        )


@pytest.mark.asyncio
async def test_update_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _acquisition_payload(status="complete", qc_state="qc_pass", transfer_state="complete")
    out = await res.update("ACQ001", status="complete", qc_state="qc_pass", transfer_state="complete")
    assert request.await_args.args[:2] == ("PATCH", "acquisitions/ACQ001")
    assert request.await_args.kwargs["json"] == {
        "status": "complete",
        "qc_state": "qc_pass",
        "transfer_state": "complete",
    }
    assert out.status == "complete"


@pytest.mark.asyncio
async def test_update_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(TypeError):
        await res.update("ACQ001", AcquisitionUpdate(status="failed"), error_message="conflict")


@pytest.mark.asyncio
async def test_add_tile_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _tile_payload()
    out = await res.add_tile(
        "ACQ001",
        raster_index=0,
        stage_position={"x": 0.0, "y": 0.0},
        raster_position={"row": 0, "col": 0},
        focus_score=0.95,
        min_value=5.0,
        max_value=255.0,
        mean_value=120.0,
        std_value=15.0,
        image={
            "protocol": "s3",
            "server": "http://localhost:9000",
            "bucket": "images",
            "key": "s3://bucket/tile-0.tiff",
        },
    )
    assert request.await_args.args[:2] == ("POST", "acquisitions/ACQ001/tiles")
    assert request.await_args.kwargs["json"]["raster_index"] == 0
    assert out.acquisition_id == "ACQ001"


@pytest.mark.asyncio
async def test_update_tile_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = _tile_payload(focus_score=0.5)
    out = await res.update_tile("ACQ001", "M001_r000_c000", focus_score=0.5)
    assert request.await_args.args[:2] == ("PATCH", "acquisitions/ACQ001/tiles/M001_r000_c000")
    assert request.await_args.kwargs["json"] == {"focus_score": 0.5}
    assert out.focus_score == 0.5


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
    request.return_value = {"urls": {"tile": _image_response()}, "metadata": _page_metadata()}
    method = getattr(resource, f"{operation}_image_urls")

    result = await method("ACQ001", tile_ids=tile_ids, expiration=300)

    request.assert_awaited_once_with(
        "POST" if operation == "put" else "GET",
        "acquisitions/ACQ001/tiles/images",
        json=tile_ids,
        params={"limit": 100, "expiration": 300},
    )
    assert result == ImageURLPage(
        urls={"tile": FileObjectResponse.model_validate(_image_response())},
        metadata=ImagePageMetadata(**_page_metadata()),
    )


async def test_all_put_image_urls_follow_pages(image_resource):
    resource, request = image_resource
    response = {
        "urls": {"tile-1": _image_response()},
        "metadata": _page_metadata(has_more=True, next_cursor="0,0,0", errors={"tile-1": "retry"}),
    }
    last_response = {"urls": {"tile-2": _image_response()}, "metadata": _page_metadata()}
    request.side_effect = [response, last_response]

    result = await resource.all_put_image_urls("ACQ001", page_limit=1)

    endpoint = "acquisitions/ACQ001/tiles/images"
    assert request.await_args_list[0].args[:2] == ("POST", endpoint)
    assert request.await_args_list[0].kwargs == {
        "json": None,
        "params": {"limit": 1},
    }
    assert request.await_args_list[1].args[:2] == ("POST", endpoint)
    assert request.await_args_list[1].kwargs == {
        "json": None,
        "params": {"cursor": "0,0,0", "limit": 1},
    }
    assert result == ImageURLs(
        urls={
            "tile-1": FileObjectResponse.model_validate(_image_response()),
            "tile-2": FileObjectResponse.model_validate(_image_response()),
        },
        errors={"tile-1": "retry"},
    )


async def test_all_get_image_urls_follows_pages_and_aggregates_errors(image_resource):
    resource, request = image_resource
    response = {
        "urls": {"tile-1": _image_response()},
        "metadata": _page_metadata(has_more=True, next_cursor="0,0,0", errors={"tile-1": "unavailable"}),
    }
    last_response = {"urls": {"tile-2": _image_response()}, "metadata": _page_metadata(errors={"tile-2": "missing"})}
    request.side_effect = [response, last_response]
    tile_ids = ["tile-1", "tile-2"]

    result = await resource.all_get_image_urls("ACQ001", tile_ids=tile_ids, expiration=300, page_limit=1)

    endpoint = "acquisitions/ACQ001/tiles/images"
    assert [call.args[:2] for call in request.await_args_list] == [("GET", endpoint), ("GET", endpoint)]
    assert [call.kwargs for call in request.await_args_list] == [
        {"json": tile_ids, "params": {"limit": 1, "expiration": 300}},
        {"json": tile_ids, "params": {"cursor": "0,0,0", "limit": 1, "expiration": 300}},
    ]
    assert result == ImageURLs(
        urls={
            "tile-1": FileObjectResponse.model_validate(_image_response()),
            "tile-2": FileObjectResponse.model_validate(_image_response()),
        },
        errors={"tile-1": "unavailable", "tile-2": "missing"},
    )


@pytest.mark.parametrize("upload_fails", [False, True])
async def test_tile_put_image_uploads_and_propagates_errors(image_resource, monkeypatch, upload_fails):
    resource, _ = image_resource
    file_object = FileObjectResponse.model_validate(_image_response())
    resource.put_image_url = AsyncMock(return_value=file_object)
    uploaded = []

    async def handle(request):
        assert request.headers["Content-Length"] == "10"
        uploaded.append(await request.aread())
        return httpx.Response(500 if upload_fails else 200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    monkeypatch.setattr("temdb.client.resources.image.httpx.AsyncClient", lambda: client)
    contents = io.BytesIO(b"tile image")

    if upload_fails:
        with pytest.raises(httpx.HTTPStatusError):
            await resource.put_image("ACQ001", "tile", contents)
    else:
        assert await resource.put_image("ACQ001", "tile", contents) is file_object

    resource.put_image_url.assert_awaited_once_with("ACQ001", "tile", None)
    assert uploaded == [b"tile image"]
    assert client.is_closed
    assert not contents.closed


@pytest.mark.parametrize("download_fails", [False, True])
async def test_tile_get_image_streams_and_propagates_errors(image_resource, download_fails, monkeypatch):
    resource, _ = image_resource
    file_object = FileObjectResponse.model_validate(_image_response())
    resource.get_image_url = AsyncMock(return_value=file_object)
    response = httpx.Response(500 if download_fails else 200, content=b"tile image")
    transport = httpx.MockTransport(lambda request: response)
    client = httpx.AsyncClient(transport=transport)
    monkeypatch.setattr("temdb.client.resources.image.httpx.AsyncClient", lambda: client)

    if download_fails:
        with pytest.raises(httpx.HTTPStatusError):
            await resource.get_image("ACQ001", "tile", expiration=300)
    else:
        image = await resource.get_image("ACQ001", "tile", expiration=300)
        assert image == b"tile image"

    resource.get_image_url.assert_awaited_once_with("ACQ001", "tile", 300)
    assert str(response.request.url) == file_object.url
    assert response.is_closed


async def test_tile_delete_image(image_resource):
    resource, request = image_resource

    await resource.delete_image("ACQ001", "tile")

    request.assert_awaited_once_with("DELETE", "acquisitions/ACQ001/tiles/tile/image")


@pytest.mark.parametrize("tile_ids", [None, ["tile"]])
async def test_tile_delete_images_awaits_request_and_returns_response(image_resource, tile_ids):
    resource, request = image_resource
    request.return_value = {"deleted_images": ["tile"], "metadata": _page_metadata()}

    result = await resource.delete_images("ACQ001", tile_ids=tile_ids)

    request.assert_awaited_once_with(
        "DELETE",
        "acquisitions/ACQ001/tiles/images",
        json=tile_ids,
        params={"limit": 100},
    )
    assert result == DeletedImagePage(deleted_images=["tile"], metadata=ImagePageMetadata(**_page_metadata()))


async def test_delete_all_images_follows_pages(image_resource):
    resource, request = image_resource
    request.side_effect = [
        {
            "deleted_images": ["tile-1"],
            "metadata": _page_metadata(has_more=True, next_cursor="0,0,0", errors={"tile-1": "retry"}),
        },
        {"deleted_images": ["tile-2"], "metadata": _page_metadata()},
    ]

    result = await resource.delete_all_images("ACQ001", page_limit=1)

    assert [call.kwargs["params"] for call in request.await_args_list] == [
        {"limit": 1},
        {"cursor": "0,0,0", "limit": 1},
    ]
    assert result == DeletedImages(deleted=["tile-1", "tile-2"], errors={"tile-1": "retry"})
