import logging

import pytest
from testcontainers.postgres import PostgresContainer

from temdb.server.database import DatabaseManager
from temdb.server.sqlmodels import Base

logging.basicConfig(level=logging.INFO)


def _async_database_url(container: PostgresContainer) -> str:
    url = container.get_connection_url()
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as container:
        yield container


@pytest.fixture(scope="function")
async def test_db_manager(postgres_container):
    db_manager = DatabaseManager(database_url=_async_database_url(postgres_container))
    await db_manager.initialize()
    yield db_manager
    if db_manager.sql_engine is not None:
        await db_manager.sql_engine.dispose()


@pytest.fixture(scope="function")
async def init_db(test_db_manager: DatabaseManager):
    if test_db_manager.sql_engine is None:
        raise RuntimeError("SQL engine is not configured for integration tests.")
    async with test_db_manager.sql_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield test_db_manager
