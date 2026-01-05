import logging

import pytest
from beanie import init_beanie
from pymongo import AsyncMongoClient
from temdb.server.documents import (
    AcquisitionDocument,
    AcquisitionTaskDocument,
    BlockDocument,
    CuttingSessionDocument,
    ROIDocument,
    SectionDocument,
    SpecimenDocument,
    SubstrateDocument,
    TileDocument,
)
from testcontainers.mongodb import MongoDbContainer

logging.basicConfig(level=logging.INFO)

TEST_DB_NAME = "testdb"

DOCUMENT_MODELS = [
    AcquisitionDocument,
    TileDocument,
    ROIDocument,
    AcquisitionTaskDocument,
    SpecimenDocument,
    BlockDocument,
    CuttingSessionDocument,
    SectionDocument,
    SubstrateDocument,
]


@pytest.fixture(scope="session")
def mongo_container():
    with MongoDbContainer("mongo:8") as container:
        yield container


@pytest.fixture(scope="function")
async def mongo_client(mongo_container):
    connection_url = mongo_container.get_connection_url()
    client = AsyncMongoClient(connection_url)
    yield client
    await client.close()


@pytest.fixture(scope="function")
async def init_db(mongo_client):
    db = mongo_client[TEST_DB_NAME]

    collections = await db.list_collection_names()
    for collection_name in collections:
        if not collection_name.startswith("system."):
            await db[collection_name].delete_many({})

    await init_beanie(
        database=db,
        document_models=DOCUMENT_MODELS,
    )
    yield db
