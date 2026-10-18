import httpx
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Match


class RecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, app: FastAPI):
        self.app = app
        self._inner = httpx.ASGITransport(app=app)
        self.requests: list[tuple[str, str]] = []
        self.gzipped_requests: list[tuple[str, str]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path))
        if request.headers.get("content-encoding") == "gzip":
            self.gzipped_requests.append((request.method, request.url.path))
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()

    def unmatched_requests(self) -> list[tuple[str, str]]:
        return unmatched_requests(self.app, self.requests)


def unmatched_requests(app: FastAPI, requests: list[tuple[str, str]]) -> list[tuple[str, str]]:
    routes = [route for route in app.routes if isinstance(route, APIRoute)]
    unmatched = []
    for method, path in requests:
        scope = {"type": "http", "method": method, "path": path, "root_path": ""}
        if not any(route.matches(scope)[0] is Match.FULL for route in routes):
            unmatched.append((method, path))
    return unmatched
