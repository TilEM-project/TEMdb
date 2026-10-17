import pytest
import pytest_asyncio

from temdb.server.main import create_app
from tests.integration.client.live import LiveServer, Seed


@pytest.fixture(scope="session")
def live_app():
    return create_app()


@pytest_asyncio.fixture
async def live(live_app, init_db):
    server = LiveServer(live_app, init_db)
    try:
        yield server
    finally:
        await server.client.close()
        live_app.dependency_overrides = {}
    assert server.unmatched_requests() == []


@pytest.fixture
def seed(live):
    return Seed(live.client)
