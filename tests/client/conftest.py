import json
from dataclasses import dataclass

import httpx
import pytest
import pytest_asyncio

from temdb.client import AsyncTEMdbClient, SyncTEMdbClient


@dataclass
class CapturedRequest:
    method: str
    path: str
    body: dict | list | None
    params: dict[str, str]

    @classmethod
    def from_httpx(cls, req: httpx.Request) -> "CapturedRequest":
        raw = req.content
        body: dict | list | None
        if not raw:
            body = None
        else:
            if req.headers.get("Content-Encoding") == "gzip":
                import gzip

                raw = gzip.decompress(raw)
            body = json.loads(raw.decode("utf-8"))
        return cls(
            method=req.method,
            path=req.url.path,
            body=body,
            params=dict(req.url.params),
        )


@pytest.fixture
def captured() -> list[CapturedRequest]:
    return []


@pytest.fixture
def response_queue() -> list[httpx.Response]:
    """Tests can push canned responses; defaults to 200 {"ok": true}."""
    return []


def _mock_transport(captured, response_queue) -> httpx.MockTransport:
    def handler(req: httpx.Request) -> httpx.Response:
        captured.append(CapturedRequest.from_httpx(req))
        if response_queue:
            return response_queue.pop(0)
        return httpx.Response(200, json={"ok": True})

    return httpx.MockTransport(handler)


@pytest_asyncio.fixture
async def client(captured: list[CapturedRequest], response_queue: list[httpx.Response]):
    c = AsyncTEMdbClient(
        base_url="http://test.invalid",
        transport=_mock_transport(captured, response_queue),
    )
    try:
        yield c
    finally:
        await c.close()


@pytest.fixture
def sync_client(captured: list[CapturedRequest], response_queue: list[httpx.Response]):
    c = SyncTEMdbClient(
        base_url="http://test.invalid",
        transport=_mock_transport(captured, response_queue),
    )
    try:
        yield c
    finally:
        c.close()
