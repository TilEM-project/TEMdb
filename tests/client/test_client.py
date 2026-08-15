from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from temdb.client import TEMdbClient
from temdb.client.exceptions import (
    TEMdbNotFoundError,
    TEMdbServerError,
    TEMdbUnprocessableError,
)
from temdb.models import SpecimenCreate


@pytest.mark.asyncio
async def test_client_initialization(client):
    assert isinstance(client, TEMdbClient)


@pytest.mark.asyncio
async def test_resource_creation(client):
    assert hasattr(client, "specimen")
    assert hasattr(client, "block")
    assert hasattr(client, "cutting_session")
    assert hasattr(client, "substrate")
    assert hasattr(client, "acquisition_task")
    assert hasattr(client, "roi")
    assert hasattr(client, "acquisition")


@pytest.mark.asyncio
async def test_extra_datetime(client):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"id": 1, "specimen_id": "test"}

    client._http_client.request = AsyncMock(return_value=mock_response)
    await client.specimen.create(
        SpecimenCreate(
            specimen_id="test",
            created_at=datetime.now(),
        )
    )


def test_server_error_maps_status_and_context():
    req = httpx.Request("GET", "https://api.temdb.example.com/api/v2/specimens/NOPE")
    resp = httpx.Response(
        404,
        request=req,
        json={"detail": "Resource not found", "context": {"traceback": "stacktrace"}},
    )
    err = httpx.HTTPStatusError("404 error", request=req, response=resp)

    mapped = TEMdbServerError.from_httpx_status_error(err)

    assert isinstance(mapped, TEMdbNotFoundError)
    assert mapped.code == 404
    assert mapped.traceback == "stacktrace"
    assert "https://api.temdb.example.com/api/v2/specimens/NOPE: Resource not found" == str(mapped)


def test_server_error_non_json_fallback_uses_response_text():
    req = httpx.Request("GET", "https://api.temdb.example.com/api/v2/health")
    resp = httpx.Response(503, request=req, text="upstream unavailable")
    err = httpx.HTTPStatusError("503 error", request=req, response=resp)

    mapped = TEMdbServerError.from_httpx_status_error(err)

    assert isinstance(mapped, TEMdbServerError)
    assert mapped.code == 503
    assert mapped.traceback is None
    assert "upstream unavailable" in str(mapped)


@pytest.mark.asyncio
async def test_async_request_raises_mapped_server_error(client):
    req = httpx.Request("PATCH", "https://api.temdb.example.com/api/v2/acquisitions/ACQ1")
    resp = httpx.Response(
        422,
        request=req,
        json={"detail": "Validation failed", "context": {"traceback": "trace-422"}},
    )
    client._http_client.request = AsyncMock(return_value=resp)

    with pytest.raises(TEMdbUnprocessableError) as exc_info:
        await client._async_request("PATCH", "acquisitions/ACQ1", json={"status": "invalid"})

    assert exc_info.value.code == 422
    assert exc_info.value.traceback == "trace-422"
    assert "Validation failed" in str(exc_info.value)
