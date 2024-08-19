import os
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI

from temdb.database import init_db
from temdb.config import Config
from temdb.api.roi import roi_api
from temdb.api.specimen import specimen_api
from temdb.api.block import block_api
from temdb.api.cutting_session import cutting_session_api
from temdb.api.section import section_api
from temdb.api.imaging_session import imaging_session_api
from temdb.api.acquisition import acquisition_api
from temdb.api.analysis import analysis_api


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
    app.state.mongo_url = os.getenv("MONGODB_URL", "mongodb://mongo:27017/")
    app.state.db_name = os.getenv("DB_NAME", "testdb")

    app.include_router(specimen_api)
    app.include_router(block_api)
    app.include_router(cutting_session_api)
    app.include_router(section_api)
    app.include_router(roi_api)
    app.include_router(imaging_session_api)
    app.include_router(acquisition_api)
    app.include_router(analysis_api)

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    @app.get("/health", response_model=dict)
    def health():
        return {"status": "ok"}

    return app
