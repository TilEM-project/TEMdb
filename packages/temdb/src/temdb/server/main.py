import gzip
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from temdb.server.api.v2.acquisition import acquisition_api
from temdb.server.api.v2.block import block_api
from temdb.server.api.v2.cutting_session import cutting_session_api
from temdb.server.api.v2.dataset import dataset_api
from temdb.server.api.v2.lens_correction import lens_correction_api
from temdb.server.api.v2.microscope import microscope_api
from temdb.server.api.v2.quality_control import qc_api
from temdb.server.api.v2.roi import roi_api
from temdb.server.api.v2.section import section_api
from temdb.server.api.v2.specimen import specimen_api
from temdb.server.api.v2.substrate import substrate_api
from temdb.server.api.v2.tasks import acquisition_task_api
from temdb.server.config import config, is_debug_traceback_enabled
from temdb.server.database import DatabaseManager
from temdb.server.exception_handlers import register_exception_handlers

__version__ = "2.0.0"

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
logger.info(f"Debug mode: {config.debug}")


class GzipRequestMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_encoding = headers.get(b"content-encoding", b"").decode()

        if content_encoding == "gzip":
            body_parts = []
            while True:
                message = await receive()
                body_parts.append(message.get("body", b""))
                if not message.get("more_body", False):
                    break

            raw_body = b"".join(body_parts)
            try:
                decompressed_body = gzip.decompress(raw_body)
            except gzip.BadGzipFile:
                decompressed_body = raw_body

            body_sent = False

            async def new_receive() -> Message:
                nonlocal body_sent
                if not body_sent:
                    body_sent = True
                    return {
                        "type": "http.request",
                        "body": decompressed_body,
                        "more_body": False,
                    }
                return {"type": "http.request", "body": b"", "more_body": False}

            await self.app(scope, new_receive, send)
        else:
            await self.app(scope, receive, send)


class DebugTracebackMiddleware:
    def __init__(self, app: ASGIApp, enabled: bool = False) -> None:
        self.app = app
        self.enabled = enabled

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            if not self.enabled:
                raise

            traceback_text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            response = JSONResponse(
                status_code=500,
                content={
                    "detail": str(exc) or "Unhandled server exception.",
                    "error_code": "INTERNAL_SERVER_ERROR",
                    "context": {"traceback": traceback_text},
                },
            )
            await response(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database_url = app.state.database_url

    logger.info(f"Connecting to SQL database: {database_url if database_url else 'disabled'}")
    db_manager = DatabaseManager(database_url)
    app.state.db_manager = db_manager
    await db_manager.initialize()
    try:
        yield
    finally:
        await db_manager.dispose()


def create_app():
    app = FastAPI(
        title=config.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(GzipRequestMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(DebugTracebackMiddleware, enabled=is_debug_traceback_enabled())
    app.config = config
    logging.info(f"SQL database URL configured: {bool(app.config.database_url)}")
    app.state.database_url = app.config.database_url

    origins = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # V2 API routes
    v2_prefix = "/api/v2"

    app.include_router(specimen_api, prefix=v2_prefix)
    app.include_router(dataset_api, prefix=v2_prefix)
    app.include_router(block_api, prefix=v2_prefix)
    app.include_router(cutting_session_api, prefix=v2_prefix)
    app.include_router(section_api, prefix=v2_prefix)
    app.include_router(substrate_api, prefix=v2_prefix)
    app.include_router(roi_api, prefix=v2_prefix)
    app.include_router(acquisition_task_api, prefix=v2_prefix)
    app.include_router(acquisition_api, prefix=v2_prefix)
    app.include_router(qc_api, prefix=v2_prefix)
    app.include_router(microscope_api, prefix=v2_prefix)
    app.include_router(lens_correction_api, prefix=v2_prefix)

    @app.get("/")
    async def root():
        return {"message": f"TEMdb API version v{__version__}"}

    @app.get("/health", response_model=dict)
    def health():
        return {"status": "ok"}

    return app
