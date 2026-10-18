import pytest
import pytest_asyncio

from temdb.client import TEMdbClient
from temdb.server.dependencies import get_db_manager
from tests.integration.client.records import Records
from tests.integration.client.transport import RecordingTransport


@pytest_asyncio.fixture
async def transport(app, init_db):
    app.dependency_overrides[get_db_manager] = lambda: init_db
    recording = RecordingTransport(app)
    try:
        yield recording
    finally:
        app.dependency_overrides = {}
    assert recording.unmatched_requests() == []


@pytest_asyncio.fixture
async def client(transport):
    client = TEMdbClient("http://test", transport=transport)
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
def records(client):
    return Records(client)
