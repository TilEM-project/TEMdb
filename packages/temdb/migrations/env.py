import asyncio
import os

import sqlalchemy as sa
from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

from temdb.server.config import get_config
from temdb.server.sqlmodels import Base

target_metadata = Base.metadata

MIGRATION_LOCK_KEY = 7_323_488_513_002_001


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table" and name.startswith("tile_d_"):
        return False
    return True


def _database_url() -> str:
    url = os.environ.get("TEMDB_MIGRATION_URL") or get_config().database_url
    if not url:
        raise RuntimeError("No database_url configured (set TEMDB_MIGRATION_URL or dev.env)")
    return url


def _configure(connection):
    connection.execute(sa.text(f"SELECT pg_advisory_lock({MIGRATION_LOCK_KEY})"))
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()
    connection.commit()


def run_migrations_offline():
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():
    cfg = context.config.get_section(context.config.config_ini_section, {})
    cfg["sqlalchemy.url"] = _database_url()
    engine = async_engine_from_config(cfg, prefix="sqlalchemy.")
    async with engine.connect() as conn:
        await conn.run_sync(_configure)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
