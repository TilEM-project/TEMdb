import asyncio
import base64
import hashlib
import io
import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import BinaryIO

import httpx

from temdb.models import FileObjectRequest, FileObjectResponse

from ..exceptions import TEMdbChecksumError

CHUNK_SIZE = 1024 * 1024


async def image_request(image_data: BinaryIO, *, hash: str | None = None, **kwargs) -> FileObjectRequest:
    """Use the supplied checksum or hash remaining bytes without changing the file position."""
    if hash is not None:
        return FileObjectRequest(hash=hash, **kwargs)

    def checksum() -> str:
        position = image_data.tell()
        digest = hashlib.sha256()
        try:
            while chunk := image_data.read(CHUNK_SIZE):
                digest.update(chunk)
        finally:
            image_data.seek(position)
        return base64.b64encode(digest.digest()).decode("ascii")

    hash_value = await asyncio.to_thread(checksum)
    return FileObjectRequest(**{**kwargs, "hash": hash_value})


async def put_image(
    file_object: FileObjectResponse, image_data: BinaryIO, client: httpx.AsyncClient | None = None
) -> FileObjectResponse:
    """Stream the caller's file without copying or closing it."""

    def remaining_size() -> int:
        position = image_data.tell()
        try:
            image_data.seek(0, os.SEEK_END)
            return image_data.tell() - position
        finally:
            image_data.seek(position)

    size = await asyncio.to_thread(remaining_size)

    async def chunks() -> AsyncIterator[bytes]:
        remaining = size
        while remaining:
            chunk = await asyncio.to_thread(image_data.read, min(CHUNK_SIZE, remaining))
            if not chunk:
                raise ValueError("Image file ended before its declared size")
            remaining -= len(chunk)
            yield chunk

    async with storage_client(client) as transfer:
        response = await transfer.put(
            file_object.url,
            content=chunks(),
            headers={"Content-Length": str(size), "x-amz-checksum-sha256": file_object.hash},
        )
        response.raise_for_status()
    return file_object


@asynccontextmanager
async def storage_client(client: httpx.AsyncClient | None) -> AsyncIterator[httpx.AsyncClient]:
    if client is not None:
        yield client
    else:
        async with httpx.AsyncClient() as owned_client:
            yield owned_client


class ImageReader:
    def __init__(self, response: httpx.Response, checksum: str):
        self._chunks = response.aiter_bytes(CHUNK_SIZE)
        self._buffer = bytearray()
        self._eof = False
        self._closed = False
        self._checksum = checksum
        self._digest = hashlib.sha256()

    async def read(self, size: int = -1) -> bytes:
        if self._closed:
            raise ValueError("Read from closed image")
        if size < -1:
            raise ValueError("size must be -1 or nonnegative")
        while not self._eof and (size == -1 or len(self._buffer) < size):
            try:
                chunk = await anext(self._chunks)
                self._digest.update(chunk)
                self._buffer.extend(chunk)
            except StopAsyncIteration:
                self._eof = True
        if self._eof and base64.b64encode(self._digest.digest()).decode("ascii") != self._checksum:
            raise TEMdbChecksumError("Downloaded image does not match its SHA-256 checksum")
        count = len(self._buffer) if size == -1 else min(size, len(self._buffer))
        result = bytes(self._buffer[:count])
        del self._buffer[:count]
        return result

    def close(self) -> None:
        self._closed = True
        self._buffer.clear()


class ImageWriter:
    def __init__(self, client: httpx.AsyncClient, url: str, size: int, checksum: str):
        self._size = size
        self._written = 0
        self._closed = False
        self._checksum = checksum
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=2)
        self._task = asyncio.create_task(self._upload(client, url))

    async def _chunks(self) -> AsyncIterator[bytes]:
        while (chunk := await self._queue.get()) is not None:
            yield chunk

    async def _upload(self, client: httpx.AsyncClient, url: str) -> None:
        response = await client.put(
            url,
            content=self._chunks(),
            headers={"Content-Length": str(self._size), "x-amz-checksum-sha256": self._checksum},
        )
        response.raise_for_status()

    async def _send(self, chunk: bytes | None) -> None:
        pending = asyncio.create_task(self._queue.put(chunk))
        try:
            await asyncio.wait((pending, self._task), return_when=asyncio.FIRST_COMPLETED)
            if self._task.done():
                await self._task
                if not pending.done():
                    raise RuntimeError("Upload completed before consuming the image data")
            await pending
        finally:
            if not pending.done():
                pending.cancel()
                await asyncio.gather(pending, return_exceptions=True)

    async def write(self, data: bytes) -> int:
        if self._closed:
            raise ValueError("Write to closed image")
        if self._written + len(data) > self._size:
            raise ValueError("Image data exceeds the declared size")
        for start in range(0, len(data), CHUNK_SIZE):
            await self._send(data[start : start + CHUNK_SIZE])
        self._written += len(data)
        return len(data)

    async def finish(self) -> None:
        self._closed = True
        if self._written != self._size:
            raise ValueError(f"Expected {self._size} image bytes, received {self._written}")
        await self._send(None)
        await self._task

    async def abort(self) -> None:
        self._closed = True
        self._task.cancel()
        await asyncio.gather(self._task, return_exceptions=True)


class BufferedImageWriter:
    def __init__(self, buffer: io.BytesIO, size: int):
        self._buffer = buffer
        self._size = size
        self._written = 0
        self._closed = False

    async def write(self, data: bytes) -> int:
        if self._closed:
            raise ValueError("Write to closed image")
        if self._written + len(data) > self._size:
            raise ValueError("Image data exceeds the declared size")
        written = self._buffer.write(data)
        self._written += written
        return written

    def finish(self) -> None:
        self._closed = True
        if self._written != self._size:
            raise ValueError(f"Expected {self._size} image bytes, received {self._written}")
        self._buffer.seek(0)

    def close(self) -> None:
        self._closed = True


@asynccontextmanager
async def open_image(
    location: Callable[[], Awaitable[FileObjectResponse]],
    mode: str,
    size: int | None = None,
    client: httpx.AsyncClient | None = None,
    *,
    upload: Callable[[BinaryIO], Awaitable[FileObjectResponse]] | None = None,
) -> AsyncIterator[ImageReader | ImageWriter | BufferedImageWriter]:
    if mode not in ("rb", "wb"):
        raise ValueError("Image mode must be 'rb' or 'wb'")
    if mode == "wb" and (size is None or isinstance(size, bool) or not isinstance(size, int) or size < 0):
        raise ValueError("Writing an image requires a nonnegative integer size")
    if mode == "wb" and upload is not None:
        assert size is not None
        with io.BytesIO() as buffer:
            writer = BufferedImageWriter(buffer, size)
            try:
                yield writer
                writer.finish()
                await upload(buffer)
            finally:
                writer.close()
        return
    file_object = await location()
    async with storage_client(client) as transfer:
        if mode == "rb":
            async with transfer.stream("GET", file_object.url) as response:
                response.raise_for_status()
                reader = ImageReader(response, file_object.hash)
                try:
                    yield reader
                finally:
                    reader.close()
        else:
            assert size is not None
            writer = ImageWriter(transfer, file_object.url, size, file_object.hash)
            try:
                yield writer
                await writer.finish()
            finally:
                await writer.abort()
