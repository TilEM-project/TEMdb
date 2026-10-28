from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import text
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer

from temdb.server.cli import run_migrations
from temdb.server.database import DatabaseManager
from temdb.server.main import create_app
from temdb.server.sqlmodels import Base
from temdb.server.storage import StorageClientManager

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


def collect_tests_using_postgres_container(items):
    for item in items:
        if "postgres_container" in item.fixturenames:
            item.add_marker(pytest.mark.db)


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def storage_client_manager(app, monkeypatch):
    manager = StorageClientManager()
    monkeypatch.setattr(app.state, "storage_client_manager", manager, raising=False)
    yield manager
    manager.close()


@pytest.fixture(scope="session")
def postgres_container():
    container = PostgresContainer("postgres:18").with_command(_UNSAFE_BUT_FAST).with_kwargs(tmpfs={_PGDATA: "rw"})
    with container:
        yield container


@pytest.fixture(scope="session")
def minio_container():
    with MinioContainer(
        image="ghcr.io/coollabsio/minio",
        access_key="temdb-test-access",
        secret_key="temdb-test-secret",
    ) as container:
        yield container


@pytest.fixture
def minio_s3(minio_container: MinioContainer, monkeypatch: pytest.MonkeyPatch):
    config = minio_container.get_config()
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", config["access_key"])
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", config["secret_key"])
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")

    bucket = f"temdb-test-{uuid4().hex[:12]}"
    client = minio_container.get_client()
    client.make_bucket(bucket)
    return {
        "server": f"http://{config['endpoint']}",
        "bucket": bucket,
        "client": client,
    }


def async_database_url(container: PostgresContainer) -> str:
    """asyncpg URL for the shared container."""
    url = container.get_connection_url()
    for prefix in ("postgresql+psycopg2://", "postgresql://", "postgres://"):
        if url.startswith(prefix):
            return url.replace(prefix, "postgresql+asyncpg://", 1)
    return url


@pytest.fixture(scope="session")
def migrated_database_url(postgres_container) -> str:
    url = async_database_url(postgres_container)
    with pytest.MonkeyPatch.context() as environment:
        environment.setenv("TEMDB_MIGRATION_URL", url)
        run_migrations(url=url)
    return url


@pytest.fixture(scope="session")
async def test_db_manager(migrated_database_url):
    db_manager = DatabaseManager(database_url=migrated_database_url)
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
