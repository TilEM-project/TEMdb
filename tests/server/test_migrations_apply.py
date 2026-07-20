import os
import subprocess

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ALEMBIC_INI = "packages/temdb/alembic.ini"


def _run_alembic(database_url: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["uv", "run", "alembic", "-c", ALEMBIC_INI, *args],
        env={**os.environ, "TEMDB_MIGRATION_URL": database_url},
        capture_output=True,
        text=True,
        check=False,
    )


async def test_upgrade_head_from_empty(fresh_database_url):
    result = _run_alembic(fresh_database_url, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    engine = create_async_engine(fresh_database_url)
    async with engine.connect() as conn:
        tables = set(
            (
                await conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
            )
            .scalars()
            .all()
        )
    await engine.dispose()
    assert {"specimens", "tiles", "lens_corrections", "microscopes", "alembic_version"} <= tables


async def test_models_match_migrations(fresh_database_url):
    _run_alembic(fresh_database_url, "upgrade", "head")
    result = _run_alembic(fresh_database_url, "check")
    assert result.returncode == 0, f"models drifted from migrations:\n{result.stdout}{result.stderr}"
