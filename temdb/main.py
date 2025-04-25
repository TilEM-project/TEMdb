import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from temdb.api.v1.grids import grid_api
from temdb.api.v2.acquisition import acquisition_api
from temdb.api.v2.quality_control import qc_api
from temdb.api.v2.block import block_api
from temdb.api.v2.cutting_session import cutting_session_api
from temdb.api.v2.substrate import substrate_api
from temdb.api.v2.tasks import acquisition_task_api
from temdb.api.v2.roi import roi_api
from temdb.api.v2.section import section_api
from temdb.api.v2.specimen import specimen_api
from temdb.config import config
from temdb.database import DatabaseManager
from temdb.exception_handlers import register_exception_handlers

__version__ = "0.1.0"

logger = logging.getLogger("uvicorn")
logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
logger.info(f"Debug mode: {config.debug}")


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
    app = FastAPI(title=config.app_name, version=__version__, lifespan=lifespan)
    app.config = config
    logging.info(f"Mongo URI: {app.config.mongodb_uri}")
    logging.info(f"Database name: {app.config.mongodb_name}")
    app.state.mongodb_uri = app.config.mongodb_uri
    app.state.mongodb_name = app.config.mongodb_name
   
    register_exception_handlers(app)

    v1_prefix = "/api/v1"
    app.include_router(grid_api, prefix=v1_prefix)

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
        return {"message": "Hello World"}

    @app.get("/health", response_model=dict)
    def health():
        return {"status": "ok"}

    return app


