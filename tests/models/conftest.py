import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from temdb.server.sqlmodels import Base


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
    with PostgresContainer("postgres:18") as container:
        yield container


@pytest.fixture(scope="function")
async def session(postgres_container):
    engine = create_async_engine(_async_database_url(postgres_container))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as db_session:
        yield db_session
    await engine.dispose()
