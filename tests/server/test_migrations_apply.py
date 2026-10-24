import os
import shutil
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = REPO_ROOT / "packages/temdb/alembic.ini"


def _run_alembic(database_url: str, *args: str) -> subprocess.CompletedProcess:
    uv_bin = shutil.which("uv")
    command = (
        [uv_bin, "run", "alembic", "-c", str(ALEMBIC_INI), *args]
        if uv_bin
        else [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), *args]
    )
    return subprocess.run(
        command,
        cwd=str(REPO_ROOT),
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
            (await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))).scalars().all()
        )
    await engine.dispose()
    assert {"specimens", "tiles", "lens_corrections", "microscopes", "alembic_version"} <= tables


async def test_models_match_migrations(fresh_database_url):
    _run_alembic(fresh_database_url, "upgrade", "head")
    result = _run_alembic(fresh_database_url, "check")
    assert result.returncode == 0, f"models drifted from migrations:\n{result.stdout}{result.stderr}"


async def test_image_storage_migration_preserves_legacy_paths(test_db_manager, test_tile):
    url = test_db_manager.sql_engine.url.render_as_string(hide_password=False)
    legacy_path = "s3://legacy-bucket/tile.tif"
    async with test_db_manager.sql_engine.begin() as conn:
        await conn.execute(text("UPDATE tiles SET image_path = :path"), {"path": legacy_path})
    try:
        result = _run_alembic(url, "downgrade", "f8a9b0c1d2e3")
        assert result.returncode == 0, result.stderr
    finally:
        result = _run_alembic(url, "upgrade", "head")
        assert result.returncode == 0, result.stderr
    async with test_db_manager.sql_engine.connect() as conn:
        stored = (await conn.execute(text("SELECT image_path, image FROM tiles"))).one()
    assert stored.image_path == legacy_path
    assert stored.image is None
