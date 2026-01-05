import gzip
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from temdb.server.api.v1.grids import grid_api
from temdb.server.api.v2.acquisition import acquisition_api
from temdb.server.api.v2.block import block_api
from temdb.server.api.v2.cutting_session import cutting_session_api
from temdb.server.api.v2.quality_control import qc_api
from temdb.server.api.v2.roi import roi_api
from temdb.server.api.v2.section import section_api
from temdb.server.api.v2.specimen import specimen_api
from temdb.server.api.v2.substrate import substrate_api
from temdb.server.api.v2.tasks import acquisition_task_api
from temdb.server.config import config
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

            compressed_body = b"".join(body_parts)
            decompressed_body = gzip.decompress(compressed_body)

            body_sent = False

            async def new_receive() -> Message:
                nonlocal body_sent
                if not body_sent:
                    body_sent = True
                    return {"type": "http.request", "body": decompressed_body, "more_body": False}
                return {"type": "http.request", "body": b"", "more_body": False}

            await self.app(scope, new_receive, send)
        else:
            await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongodb_uri = app.state.mongodb_uri
    mongodb_name = app.state.mongodb_name

    logger.info(f"Connecting to database: {mongodb_uri}, database name: {mongodb_name}")
    db_manager = DatabaseManager(mongodb_uri, mongodb_name)
    app.state.db_manager = db_manager
    await db_manager.initialize()
    yield


def create_app():
    app = FastAPI(
        title=config.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    app.add_middleware(GzipRequestMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.config = config
    logging.info(f"Mongo URI: {app.config.mongodb_uri}")
    logging.info(f"Database name: {app.config.mongodb_name}")
    app.state.mongodb_uri = app.config.mongodb_uri
    app.state.mongodb_name = app.config.mongodb_name

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

    # V1 API routes (legacy)
    v1_prefix = "/api/v1"
    app.include_router(grid_api, prefix=v1_prefix)

    # V2 API routes
    v2_prefix = "/api/v2"

    app.include_router(specimen_api, prefix=v2_prefix)
    app.include_router(block_api, prefix=v2_prefix)
    app.include_router(cutting_session_api, prefix=v2_prefix)
    app.include_router(section_api, prefix=v2_prefix)
    app.include_router(substrate_api, prefix=v2_prefix)
    app.include_router(roi_api, prefix=v2_prefix)
    app.include_router(acquisition_task_api, prefix=v2_prefix)
    app.include_router(acquisition_api, prefix=v2_prefix)
    app.include_router(qc_api, prefix=v2_prefix)

    @app.get("/")
    async def root():
        return {"message": f"TEMdb API version v{__version__}"}

    @app.get("/health", response_model=dict)
    def health():
        return {"status": "ok"}

    return app
