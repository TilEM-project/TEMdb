import asyncio
import os

import pytest
from beanie import init_beanie
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pymongo import AsyncMongoClient
from testcontainers.mongodb import MongoDbContainer

from temdb.client import AsyncTEMdbClient
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
from temdb.server.main import create_app

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
async def mongo_container():
    if "TEMDB_BASE_URL" in os.environ:
        yield None
        return
    with MongoDbContainer("mongo:8") as container:
        connection_url = container.get_connection_url()
        client = AsyncMongoClient(connection_url)
        await init_db(client)
        yield connection_url
        client.close()


async def init_db(client):
    db = client[TEST_DB_NAME]

    collections = await db.list_collection_names()
    for collection_name in collections:
        if not collection_name.startswith("system."):
            await db[collection_name].delete_many({})

    await init_beanie(
        database=db,
        document_models=DOCUMENT_MODELS,
    )
    return db


@pytest.fixture(scope="session")
def app(mongo_container, session_mocker):
    if mongo_container is None:
        yield None
        return
    session_mocker.patch("temdb.server.main.config.mongodb_uri", mongo_container)
    session_mocker.patch("temdb.server.main.config.mongodb_name", TEST_DB_NAME)
    yield create_app()


@pytest.fixture(scope="function")
async def async_client(app: FastAPI) -> AsyncClient:
    if app is None:
        async with AsyncTEMdbClient(os.environ["TEMDB_BASE_URL"]) as client:
            yield client
        return
    async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as client:
        async with AsyncTEMdbClient(base_url="http://test") as temdb_client:
            temdb_client._http_client = client
            yield temdb_client


@pytest.fixture(scope="session")
def event_loop():
    """Overrides pytest-asyncio's default function-scoped event loop."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
