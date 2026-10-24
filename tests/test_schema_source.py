from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import ValidationError
from sqlalchemy import text

from temdb import models
from temdb.server import sqlmodels


async def test_database_schema_matches_migration_head(test_db_manager):
    alembic_ini = Path(__file__).resolve().parents[1] / "packages/temdb/alembic.ini"
    head = ScriptDirectory.from_config(Config(str(alembic_ini))).get_current_head()
    async with test_db_manager.sql_engine.connect() as conn:
        version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one()
    assert version == head


@pytest.mark.parametrize(
    ("update_model", "sql_model"),
    [
        (getattr(models, name), getattr(sqlmodels, name.removesuffix("Update") + "SQLModel"))
        for name in models.__all__
        if name.endswith("Update")
    ],
)
def test_update_models_reject_null_for_not_null_columns(update_model, sql_model):
    """An update that sends null for a NOT NULL column must fail validation, not reach Postgres. Fields that are
    not columns (tile positions, the ROI payload) must reject null too. extra and aperture_status are partial
    updates, where null means no change; updated_by is an actor stamp, where null means anonymous."""
    update_model.model_validate({})
    columns = sql_model.__table__.columns
    accepts_null = []
    for name in update_model.model_fields:
        if name in ("extra", "aperture_status", "updated_by") or (name in columns and columns[name].nullable):
            continue
        try:
            update_model.model_validate({name: None})
        except ValidationError:
            continue
        accepts_null.append(name)
    assert accepts_null == []
