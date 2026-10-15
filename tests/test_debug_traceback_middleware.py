import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from temdb.server.main import create_app


@pytest.mark.asyncio
async def test_debug_true_returns_traceback(monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    app = create_app()

    @app.get("/_raise")
    async def raise_error():
        raise RuntimeError("boom")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/_raise")

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"] == "RuntimeError('boom')"
    assert payload["error_code"] == "INTERNAL_SERVER_ERROR"
    assert "context" in payload
    assert "traceback" in payload["context"]
    assert "RuntimeError: boom" in payload["context"]["traceback"]


@pytest.mark.asyncio
async def test_debug_false_hides_traceback(monkeypatch):
    monkeypatch.delenv("DEBUG", raising=False)
    app = create_app()

    @app.get("/_raise")
    async def raise_error():
        raise RuntimeError("boom")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/_raise")

    assert response.status_code == 500
    payload = response.json()
    assert payload["detail"] == "An unexpected internal server error occurred. Please contact the administrator."
    assert payload["error_code"] == "INTERNAL_SERVER_ERROR"
    assert payload.get("context") is None


@pytest.mark.asyncio
async def test_debug_true_still_answers_an_http_exception_with_the_error_body(monkeypatch):
    monkeypatch.setenv("DEBUG", "true")
    app = create_app()

    @app.get("/_http_error")
    async def raise_http_error():
        raise HTTPException(status_code=404, detail="missing")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get("/_http_error")

    assert response.status_code == 404
    payload = response.json()
    assert payload["detail"] == "missing"
    assert payload["error_code"] == "NOT_FOUND"
    assert payload.get("context") is None
