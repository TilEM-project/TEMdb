import asyncio
import importlib.metadata

import httpx
import pytest

from temdb.client import TEMdbClient
from temdb.client.exceptions import TEMdbContractError


def models_major() -> str:
    return importlib.metadata.version("temdb-models").split(".")[0]


def server(models_version: str, seen: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/api/v2/contract":
            return httpx.Response(200, json={"api": "v2", "server_version": "9.9.9", "models_version": models_version})
        return httpx.Response(200, json=[])

    return handler


@pytest.mark.asyncio
async def test_matching_major_version_is_accepted():
    """A server with the same models major version is accepted and its contract stored."""
    transport = httpx.MockTransport(server(f"{models_major()}.99.0", []))
    async with TEMdbClient("http://test", transport=transport) as client:
        assert client.contract["models_version"] == f"{models_major()}.99.0"


@pytest.mark.asyncio
async def test_mismatched_major_version_is_rejected_on_enter():
    """A server with a different models major version raises on `async with`."""
    with pytest.raises(TEMdbContractError, match="models 0.1.0"):
        async with TEMdbClient("http://test", transport=httpx.MockTransport(server("0.1.0", []))):
            pass


@pytest.mark.asyncio
async def test_missing_contract_route_warns_and_proceeds(caplog):
    """A server without /contract (3.0.0) is used after one warning and one /contract request."""
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        if request.url.path == "/api/v2/contract":
            return httpx.Response(404, json={"detail": "Not Found"})
        return httpx.Response(200, json=[])

    async with TEMdbClient("http://test", transport=httpx.MockTransport(handler)) as client:
        await client.specimen.list()
        await client.specimen.list()
    assert seen == ["/api/v2/contract", "/api/v2/specimens", "/api/v2/specimens"]
    assert [r.levelname for r in caplog.records if "no /contract" in r.getMessage()] == ["WARNING"]


@pytest.mark.asyncio
async def test_contract_is_checked_once_before_first_request():
    """Without `async with`, /contract is fetched before the first call and only once."""
    seen = []
    client = TEMdbClient("http://test", transport=httpx.MockTransport(server(f"{models_major()}.0.0", seen)))
    try:
        await client.specimen.list()
        await client.specimen.list()
    finally:
        await client.close()
    assert seen == ["/api/v2/contract", "/api/v2/specimens", "/api/v2/specimens"]


@pytest.mark.asyncio
async def test_incompatible_server_is_rejected_before_first_request():
    """An incompatible server raises before any request other than /contract is sent."""
    seen = []
    client = TEMdbClient("http://test", transport=httpx.MockTransport(server("0.1.0", seen)))
    try:
        with pytest.raises(TEMdbContractError):
            await client.specimen.list()
    finally:
        await client.close()
    assert seen == ["/api/v2/contract"]


@pytest.mark.asyncio
async def test_rejected_server_closes_the_http_client():
    """A failed `async with` closes the HTTP client."""
    client = TEMdbClient("http://test", transport=httpx.MockTransport(server("0.1.0", [])))
    with pytest.raises(TEMdbContractError):
        async with client:
            pass
    assert client._http_client.is_closed


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [{}, [], {"api": "v2", "server_version": "1", "models_version": 3}])
async def test_malformed_contract_raises_contract_error(body):
    """A /contract body of the wrong shape raises TEMdbContractError."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    with pytest.raises(TEMdbContractError):
        async with TEMdbClient("http://test", transport=httpx.MockTransport(handler)):
            pass


@pytest.mark.asyncio
async def test_concurrent_first_requests_share_one_contract_check():
    """Concurrent first requests on a fresh client fetch /contract once."""
    seen = []
    answer = server(f"{models_major()}.0.0", seen)

    async def slow_server(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0)
        return answer(request)

    client = TEMdbClient("http://test", transport=httpx.MockTransport(slow_server))
    try:
        await asyncio.gather(*(client.specimen.list() for _ in range(5)))
    finally:
        await client.close()
    assert seen.count("/api/v2/contract") == 1
