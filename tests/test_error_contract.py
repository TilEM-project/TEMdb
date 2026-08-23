import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from temdb.client.exceptions import TEMdbServerError, TEMdbUnprocessableError
from temdb.server.exception_handlers import register_exception_handlers


class _Body(BaseModel):
    specimen_id: str
    tile_count: int


@pytest.fixture
def app():
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/things")
    async def create_thing(body: _Body):
        return {"ok": True}

    return app


def _as_client_error(response):
    return TEMdbServerError.from_httpx_status_error(
        httpx.HTTPStatusError("error", request=response.request, response=response)
    )


@pytest.mark.asyncio
async def test_validation_failure_tells_the_caller_which_field(app):
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.post("/things", json={"tile_count": "abc"})

    assert response.status_code == 422

    error = _as_client_error(response)

    assert isinstance(error, TEMdbUnprocessableError)
    assert error.error_code == "VALIDATION_ERROR"
    assert "body.specimen_id: Field required" in str(error)
    assert "body.tile_count" in str(error)
    assert {tuple(e["loc"]) for e in error.context["errors"]} == {
        ("body", "specimen_id"),
        ("body", "tile_count"),
    }
