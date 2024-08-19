import pytest
import logging
import asyncio
import time
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from temdb.models.acquisition import Acquisition
from temdb.models.tile import Tile
from temdb.models.roi import ROI
from temdb.models.imaging_session import ImagingSession
from temdb.models.specimen import Specimen
from temdb.models.block import Block
from temdb.models.cutting_session import CuttingSession
from temdb.models.section import Section
import pymongo

logging.basicConfig(level=logging.INFO)

DATABASE_URL = "mongodb://localhost:27017/testdb"

@pytest.fixture(scope="session")
async def mongo_client():
    logging.info(f"Connecting to database: {DATABASE_URL}")
    retries = 5
    for i in range(retries):
        try:
            client = AsyncIOMotorClient(DATABASE_URL)
            client.get_io_loop = asyncio.get_event_loop
            await client.admin.command('ping')
            logging.info("Connected to database")
            yield client
            client.close()
            break
        except pymongo.errors.ConnectionFailure as e:
            logging.info(f"MongoDB not ready yet: {str(e)}, retrying...")
            time.sleep(5)
    else:
        logging.error("Could not connect to MongoDB after several retries")
        pytest.fail("MongoDB did not start in time")

@pytest.fixture(scope="session")
async def init_db(mongo_client):
    await init_beanie(
        database=mongo_client.get_database("testdb"),
        document_models=[
            Acquisition,
            Tile,
            ROI,
            ImagingSession,
            Specimen,
            Block,
            CuttingSession,
            Section,
        ],
    )
    yield
    await mongo_client.drop_database("testdb")
