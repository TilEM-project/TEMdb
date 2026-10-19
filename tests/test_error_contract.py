import httpx
import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy import select

from temdb.client.exceptions import (
    TEMdbConflictError,
    TEMdbInternalError,
    TEMdbServerError,
    TEMdbUnprocessableError,
)
from temdb.models import APIErrorResponse
from temdb.server.exception_handlers import register_exception_handlers
from temdb.server.sqlmodels import AcquisitionTaskSQLModel, LensCorrectionSQLModel, SpecimenSQLModel


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

    @app.get("/things/{thing_id}")
    async def get_thing(thing_id: str):
        raise HTTPException(status_code=404, detail=f"Thing '{thing_id}' not found")

    @app.post("/things/{thing_id}/conflict")
    async def conflict(thing_id: str):
        raise HTTPException(status_code=409, detail={"thing_ids": [thing_id]})

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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "status", "error_code"),
    [
        ("GET", "/things/T1", 404, "NOT_FOUND"),
        ("GET", "/no/such/route", 404, "NOT_FOUND"),
        ("POST", "/things", 422, "VALIDATION_ERROR"),
        ("POST", "/things/T1/conflict", 409, "CONFLICT"),
    ],
)
async def test_every_error_body_is_an_api_error_response(app, method, path, status, error_code):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, path, json={})

    assert response.status_code == status
    body = APIErrorResponse.model_validate(response.json())
    assert body.error_code == error_code
    assert body.detail


@pytest.mark.asyncio
async def test_structured_http_exception_detail_moves_to_context(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/things/T1/conflict")

    error = _as_client_error(response)
    assert isinstance(error, TEMdbConflictError)
    assert error.error_code == "CONFLICT"
    assert error.context == {"detail": {"thing_ids": ["T1"]}}


@pytest.fixture
def database_app(app, init_db):
    """Routes that go straight to Postgres, as an endpoint does once its pre-checks have passed."""

    @app.get("/specimens")
    async def page_specimens(skip: int):
        async with init_db.async_session_factory() as session:
            await session.scalars(select(SpecimenSQLModel).offset(skip))
        return {"ok": True}

    @app.get("/lens-corrections")
    async def find_lens_corrections(magnification: int):
        async with init_db.async_session_factory() as session:
            await session.scalars(
                select(LensCorrectionSQLModel).where(LensCorrectionSQLModel.magnification == magnification)
            )
        return {"ok": True}

    @app.post("/specimens/{specimen_id}")
    async def insert_specimen(specimen_id: str):
        async with init_db.async_session_factory() as session:
            session.add(SpecimenSQLModel(specimen_id=specimen_id))
            await session.commit()
        return {"ok": True}

    @app.post("/tasks/{task_id}")
    async def insert_task_without_lineage(task_id: str):
        async with init_db.async_session_factory() as session:
            session.add(AcquisitionTaskSQLModel(task_id=task_id))
            await session.commit()
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_unique_violation_is_a_conflict_naming_the_table(database_app):
    async with AsyncClient(
        transport=ASGITransport(app=database_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        assert (await client.post("/specimens/RACED")).status_code == 200
        response = await client.post("/specimens/RACED")

    assert response.status_code == 409

    error = _as_client_error(response)

    assert isinstance(error, TEMdbConflictError)
    assert error.error_code == "UNIQUE_VIOLATION"
    assert error.context["table"] == SpecimenSQLModel.__tablename__
    assert "RACED" in str(error)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        f"/specimens?skip={2**63}",
        f"/lens-corrections?magnification={2**31}",
    ],
)
async def test_integer_too_large_for_its_column_is_a_validation_error(database_app, path):
    async with AsyncClient(
        transport=ASGITransport(app=database_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get(path)

    assert response.status_code == 422

    error = _as_client_error(response)

    assert isinstance(error, TEMdbUnprocessableError)
    assert error.error_code == "VALIDATION_ERROR"
    assert "Number out of range" in str(error)


@pytest.mark.asyncio
async def test_other_integrity_violations_stay_internal_errors(database_app, monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    async with AsyncClient(
        transport=ASGITransport(app=database_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.post("/tasks/NO_LINEAGE")

    assert response.status_code == 500
    assert isinstance(_as_client_error(response), TEMdbInternalError)
