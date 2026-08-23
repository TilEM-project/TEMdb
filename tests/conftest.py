import pytest
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer

from temdb.server.database import DatabaseManager
from temdb.server.sqlmodels import Base

_UNSAFE_BUT_FAST = (
    "-c fsync=off "
    "-c synchronous_commit=off "
    "-c full_page_writes=off "
    "-c autovacuum=off "
    "-c checkpoint_timeout=1d "
    "-c max_wal_size=4GB "
    "-c shared_buffers=64MB"
)

_PGDATA = "/var/lib/postgresql/18/docker"


@pytest.fixture(scope="session")
def postgres_container():
    container = PostgresContainer("postgres:18").with_command(_UNSAFE_BUT_FAST).with_kwargs(tmpfs={_PGDATA: "rw"})
    with container:
        yield container


def async_database_url(container: PostgresContainer) -> str:
    """asyncpg URL for the shared container."""
    url = container.get_connection_url()
    for prefix in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return url.replace(prefix, "postgresql+asyncpg://", 1)
    return url


@pytest.fixture(scope="session")
async def test_db_manager(postgres_container):
    db_manager = DatabaseManager(database_url=async_database_url(postgres_container))
    await db_manager.initialize(create_schema=True)
    yield db_manager
    await db_manager.dispose()


_TILE_PARTITIONS = text(
    "SELECT c.relname FROM pg_class c "
    "JOIN pg_inherits i ON i.inhrelid = c.oid "
    "JOIN pg_class p ON p.oid = i.inhparent "
    "WHERE p.relname = 'tiles'"
)

_DELETE_ORDER = tuple(table.delete() for table in reversed(Base.metadata.sorted_tables))


@pytest.fixture(scope="function")
async def init_db(test_db_manager: DatabaseManager) -> DatabaseManager:
    async with test_db_manager.sql_engine.begin() as conn:
        for partition in (await conn.execute(_TILE_PARTITIONS)).scalars():
            await conn.execute(text(f'DROP TABLE IF EXISTS "{partition}" CASCADE'))
        for statement in _DELETE_ORDER:
            await conn.execute(statement)
    return test_db_manager
