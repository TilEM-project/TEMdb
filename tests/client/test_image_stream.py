import asyncio
import base64
import hashlib
import io
from unittest.mock import AsyncMock

import httpx
import pytest

from temdb.client.exceptions import TEMdbChecksumError
from temdb.client.resources.acquisition import AcquisitionResource
from temdb.client.resources.image import (
    CHUNK_SIZE,
    BufferedImageWriter,
    ImageWriter,
    image_request,
    open_image,
    put_image,
)
from temdb.client.resources.section import SectionResource
from temdb.models import FileObjectResponse


def checksum(data):
    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


@pytest.fixture
def location():
    return AsyncMock(
        return_value=FileObjectResponse(
            protocol="s3",
            server="http://storage",
            bucket="images",
            key="tile",
            url="http://storage/images/tile",
            expiration=300,
            hash=checksum(b"image"),
        )
    )


@pytest.mark.parametrize("mode,size", [("r", None), ("w", None), ("wb", None), ("wb", -1), ("wb", True)])
async def test_invalid_open_fails_before_request(location, mode, size):
    with pytest.raises(ValueError):
        async with open_image(location, mode, size):
            pytest.fail("Invalid stream opened")
    location.assert_not_awaited()


@pytest.mark.parametrize("size", [0, 11, CHUNK_SIZE * 3 + 7])
async def test_streamed_write_sends_declared_size(location, monkeypatch, size):
    received = bytearray()

    async def handle(request):
        assert request.headers["Content-Length"] == str(size)
        assert request.headers["x-amz-checksum-sha256"] == location.return_value.hash
        async for chunk in request.stream:
            received.extend(chunk)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    monkeypatch.setattr("temdb.client.resources.image.httpx.AsyncClient", lambda: client)
    async with open_image(location, "wb", size) as image:
        assert await image.write(b"x" * size) == size
    assert received == b"x" * size
    with pytest.raises(ValueError, match="closed"):
        await image.write(b"x")


@pytest.mark.parametrize("contents", [b"short", b"too long for size"])
async def test_streamed_write_rejects_size_mismatch(location, monkeypatch, contents):
    async def handle(request):
        await request.aread()
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    monkeypatch.setattr("temdb.client.resources.image.httpx.AsyncClient", lambda: client)
    with pytest.raises(ValueError):
        async with open_image(location, "wb", 10) as image:
            await image.write(contents)


async def test_body_failure_cancels_upload(location, monkeypatch):
    started = asyncio.Event()
    cancelled = asyncio.Event()

    class Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            started.set()
            try:
                await request.aread()
            except asyncio.CancelledError:
                cancelled.set()
                raise
            return httpx.Response(200)

    client = httpx.AsyncClient(transport=Transport())
    monkeypatch.setattr("temdb.client.resources.image.httpx.AsyncClient", lambda: client)
    with pytest.raises(ValueError, match="interrupted"):
        async with open_image(location, "wb", CHUNK_SIZE * 5) as image:
            await image.write(b"x")
            await started.wait()
            raise ValueError("interrupted")
    assert cancelled.is_set()


async def test_upload_failure_unblocks_writer():
    class Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            raise httpx.ConnectError("storage unavailable")

    async with httpx.AsyncClient(transport=Transport()) as client:
        writer = ImageWriter(client, "http://storage/image", CHUNK_SIZE * 10, checksum(b"x" * CHUNK_SIZE * 10))
        try:
            with pytest.raises(httpx.ConnectError, match="storage unavailable"):
                await asyncio.wait_for(writer.write(b"x" * (CHUNK_SIZE * 10)), timeout=2)
        finally:
            await writer.abort()


async def test_writer_applies_backpressure():
    started = asyncio.Event()
    release = asyncio.Event()

    class Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            started.set()
            await release.wait()
            await request.aread()
            return httpx.Response(200)

    async with httpx.AsyncClient(transport=Transport()) as client:
        writer = ImageWriter(client, "http://storage/image", CHUNK_SIZE * 5, checksum(b"x" * CHUNK_SIZE * 5))
        pending = asyncio.create_task(writer.write(b"x" * CHUNK_SIZE * 5))
        try:
            await started.wait()
            await asyncio.sleep(0)
            assert not pending.done()
            release.set()
            assert await asyncio.wait_for(pending, timeout=2) == CHUNK_SIZE * 5
            await writer.finish()
        finally:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
            await writer.abort()


@pytest.mark.parametrize("size", [0, CHUNK_SIZE * 3 + 7])
async def test_direct_upload_streams_remaining_file_in_bounded_chunks(location, size):
    class File(io.BytesIO):
        def read(self, count=-1):
            assert 0 < count <= CHUNK_SIZE
            return super().read(count)

    received = bytearray()

    class Transport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            assert request.headers["Content-Length"] == str(size)
            assert request.headers["x-amz-checksum-sha256"] == file_object.hash
            async for chunk in request.stream:
                assert len(chunk) <= CHUNK_SIZE
                received.extend(chunk)
            return httpx.Response(200)

    contents = File(b"skip" + b"x" * size)
    contents.seek(4)
    file_object = await location()
    file_object.hash = checksum(b"x" * size)
    async with httpx.AsyncClient(transport=Transport()) as client:
        assert await put_image(file_object, contents, client) is file_object
        assert not client.is_closed
    assert received == b"x" * size
    assert not contents.closed


async def test_open_image_reuses_supplied_client_without_closing_it(location):
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"image")))
    try:
        for _ in range(2):
            async with open_image(location, "rb", client=client) as image:
                assert await image.read() == b"image"
            assert not client.is_closed
    finally:
        await client.aclose()


@pytest.mark.parametrize("size", [0, CHUNK_SIZE * 2 + 7])
async def test_image_request_hashes_remaining_bytes_and_preserves_position_and_location(size):
    class File(io.BytesIO):
        def read(self, count=-1):
            assert 0 < count <= CHUNK_SIZE
            return super().read(count)

    contents = File(b"skip" + b"x" * size)
    contents.seek(4)
    result = await image_request(contents, key="custom.tif")
    assert result.hash == checksum(b"x" * size)
    assert result.key == "custom.tif"
    assert contents.tell() == 4
    assert not contents.closed


async def test_image_request_uses_supplied_checksum_without_reading_file():
    class File(io.BytesIO):
        def read(self, count=-1):
            pytest.fail("File was read despite a supplied checksum")

    contents = File(b"skipimage")
    contents.seek(4)
    result = await image_request(contents, hash=checksum(b"image"), key="custom.tif", expiration=600)
    assert result.hash == checksum(b"image")
    assert result.key == "custom.tif"
    assert result.expiration == 600
    assert contents.tell() == 4


async def test_image_request_restores_position_on_read_failure():
    class File(io.BytesIO):
        def read(self, count=-1):
            super().read(count)
            raise OSError("read failed")

    contents = File(b"skipimage")
    contents.seek(4)
    with pytest.raises(OSError, match="read failed"):
        await image_request(contents)
    assert contents.tell() == 4


@pytest.mark.parametrize("contents", [b"", b"image", b"x" * (CHUNK_SIZE * 2 + 7)])
@pytest.mark.parametrize("corrupt", [False, True])
async def test_download_verifies_checksum_at_eof(location, contents, corrupt):
    location.return_value.hash = checksum(contents if not corrupt else b"different")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=contents))
    ) as client:
        async with open_image(location, "rb", client=client) as image:
            if corrupt:
                with pytest.raises(TEMdbChecksumError):
                    await image.read()
            else:
                assert await image.read() == contents


async def test_partial_download_does_not_claim_integrity(location):
    location.return_value.hash = checksum(b"different")
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"image"))
    ) as client:
        async with open_image(location, "rb", client=client) as image:
            assert await image.read(2) == b"im"
            with pytest.raises(TEMdbChecksumError):
                await image.read()


@pytest.fixture(params=[SectionResource, AcquisitionResource])
def image_resource(request):
    api = AsyncMock()
    resource = request.param(api, "http://test/api/v2")
    ids = ("SEC001",) if request.param is SectionResource else ("ACQ001", "tile")
    return resource, api, ids


@pytest.mark.parametrize("size", [0, CHUNK_SIZE * 2 + 7])
async def test_resource_buffers_until_exit_and_forwards_storage_keywords(image_resource, location, size):
    resource, api, ids = image_resource
    contents = b"x" * size
    location.return_value.hash = checksum(contents)
    api.return_value = location.return_value.model_dump()
    received = []

    async def handle(request):
        assert request.headers["x-amz-checksum-sha256"] == checksum(contents)
        received.append(await request.aread())
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        resource._file_client = client
        async with resource.open_image(*ids, "wb", size=size, key="custom.tif", expiration=600) as image:
            assert isinstance(image, BufferedImageWriter)
            await image.write(contents[:5])
            await image.write(contents[5:])
            api.assert_not_awaited()
            assert not received
        assert not client.is_closed
    assert received == [contents]
    assert api.await_args.kwargs["json"] == {"key": "custom.tif", "expiration": 600, "hash": checksum(contents)}
    assert image._buffer.closed
    with pytest.raises(ValueError, match="closed"):
        await image.write(b"")


@pytest.mark.parametrize("failure", ["short", "long", "body", "upload"])
async def test_buffered_failure_closes_buffer(image_resource, location, failure):
    resource, api, ids = image_resource
    api.return_value = location.return_value.model_dump()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(500))) as client:
        resource._file_client = client
        error = httpx.HTTPStatusError if failure == "upload" else ValueError
        with pytest.raises(error):
            async with resource.open_image(*ids, "wb", size=5) as image:
                await image.write(b"toolong" if failure == "long" else b"x" if failure == "short" else b"image")
                if failure == "body":
                    raise ValueError("interrupted")
        assert image._buffer.closed
    if failure != "upload":
        api.assert_not_awaited()


async def test_resource_streams_directly_with_supplied_hash(image_resource, location):
    resource, api, ids = image_resource
    api.return_value = location.return_value.model_dump()
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200))) as client:
        resource._file_client = client
        async with resource.open_image(
            *ids, "wb", size=5, hash=checksum(b"image"), key="custom.tif", expiration=600
        ) as image:
            assert isinstance(image, ImageWriter)
            api.assert_awaited_once()
            await image.write(b"image")
    assert api.await_args.kwargs["json"] == {"key": "custom.tif", "expiration": 600, "hash": checksum(b"image")}


@pytest.mark.parametrize("method", ["put_image", "buffered", "streamed"])
async def test_explicit_storage_location_is_forwarded(image_resource, location, method):
    resource, api, ids = image_resource
    api.return_value = location.return_value.model_dump()
    options = {
        "protocol": "s3",
        "server": "http://custom-storage",
        "bucket": "custom-images",
        "key": "/custom.tif",
    }
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200))) as client:
        resource._file_client = client
        if method == "put_image":
            await resource.put_image(*ids, io.BytesIO(b"image"), **options)
        else:
            async with resource.open_image(
                *ids, "wb", size=5, hash=checksum(b"image") if method == "streamed" else None, **options
            ) as image:
                await image.write(b"image")
    payload = api.await_args.kwargs["json"]
    assert {name: payload[name] for name in options} == options
    assert payload["hash"] == checksum(b"image")
