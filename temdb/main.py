import os
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI

from temdb.database import init_db
from temdb.config import Config

from temdb.api.v1.grids import grid_api

from temdb.api.v2.roi import roi_api
from temdb.api.v2.specimen import specimen_api
from temdb.api.v2.block import block_api
from temdb.api.v2.cutting_session import cutting_session_api
from temdb.api.v2.section import section_api
from temdb.api.v2.imaging_session import imaging_session_api
from temdb.api.v2.acquisition import acquisition_api
from temdb.api.v2.analysis import analysis_api


__version__ = "0.1.0"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongo_url = app.state.mongo_url
    db_name = app.state.db_name

    logger.info(f"Connecting to database: {mongo_url}, database name: {db_name}")
    await init_db(mongo_url, db_name)
    yield


def create_app():
    app = FastAPI(title="TEMDB", version=__version__, lifespan=lifespan)
    app.config = Config()
    logging.info(f"Mongo URL: {app.config.MONGODB_URL}")
    logging.info(f"Database name: {app.config.DB_NAME}")
    app.state.mongo_url = app.config.MONGODB_URL
    app.state.db_name = app.config.DB_NAME

    v1_prefix = "/api/v1"
    app.include_router(grid_api, prefix=v1_prefix)

    v2_prefix = "/api/v2"

    app.include_router(specimen_api, prefix=v2_prefix)
    app.include_router(block_api, prefix=v2_prefix)
    app.include_router(cutting_session_api, prefix=v2_prefix)
    app.include_router(section_api, prefix=v2_prefix)
    app.include_router(roi_api, prefix=v2_prefix)
    app.include_router(imaging_session_api, prefix=v2_prefix)
    app.include_router(acquisition_api, prefix=v2_prefix)
    app.include_router(analysis_api, prefix=v2_prefix)

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    @app.get("/health", response_model=dict)
    def health():
        return {"status": "ok"}

    return app
