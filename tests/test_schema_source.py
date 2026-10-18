from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text


async def test_database_schema_matches_migration_head(test_db_manager):
    alembic_ini = Path(__file__).resolve().parents[1] / "packages/temdb/alembic.ini"
    head = ScriptDirectory.from_config(Config(str(alembic_ini))).get_current_head()
    async with test_db_manager.sql_engine.connect() as conn:
        version = (
            await conn.execute(text("SELECT version_num FROM alembic_version"))
        ).scalar_one()
    assert version == head
