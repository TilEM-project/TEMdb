import pytest

from temdb.server.database import DatabaseManager


@pytest.fixture(scope="function")
async def session(init_db: DatabaseManager):
    async with init_db.async_session_factory() as db_session:
        yield db_session
