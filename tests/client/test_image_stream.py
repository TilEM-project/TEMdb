import asyncio
import io
from unittest.mock import AsyncMock

import httpx
import pytest

from temdb.client.resources.image import CHUNK_SIZE, ImageWriter, open_image, put_image
from temdb.models import FileObjectResponse


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
        writer = ImageWriter(client, "http://storage/image", CHUNK_SIZE * 10)
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
        writer = ImageWriter(client, "http://storage/image", CHUNK_SIZE * 5)
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
            async for chunk in request.stream:
                assert len(chunk) <= CHUNK_SIZE
                received.extend(chunk)
            return httpx.Response(200)

    contents = File(b"skip" + b"x" * size)
    contents.seek(4)
    file_object = await location()
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
