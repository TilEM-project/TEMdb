from datetime import datetime, timedelta, timezone

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import create_async_engine

from tests.server.test_migrations_apply import _run_alembic

pickup = datetime(2026, 8, 19, 15, 53, 51, tzinfo=timezone.utc)


def stub(name: str, *columns: str) -> sa.TableClause:
    types = {"extra": JSONB(), "aperture_status": ARRAY(sa.String())}
    return sa.table(name, *(sa.column(column, types.get(column)) for column in columns))


specimens = stub("specimens", "specimen_id", "extra")
blocks = stub("blocks", "block_id", "specimen_id", "extra")
cutting_sessions = stub(
    "cutting_sessions",
    "cutting_session_id",
    "specimen_id",
    "block_id",
    "start_time",
    "sectioning_device",
    "media_type",
    "extra",
)
layouts = stub("layouts", "layout_id", "media_type", "extra")
substrates = stub("substrates", "media_id", "substrate_layout_id", "aperture_status", "extra")
sections = stub(
    "sections",
    "section_id",
    "section_number",
    "timestamp",
    "cutting_session_id",
    "block_id",
    "specimen_id",
    "media_id",
    "aperture_index",
    "extra",
)
rois = stub(
    "rois",
    "roi_id",
    "roi_number",
    "section_id",
    "block_id",
    "specimen_id",
    "substrate_media_id",
    "hierarchy_level",
    "extra",
)


async def seed_overwritten_groups(database_url: str, roi_on: str | None = None) -> None:
    """Substrate 001123 at the revision before the sections migration: S5, S6 and S10 share aperture 2 and one
    timestamp, S2 and S8 share aperture 0 and another, S11 sits alone."""
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.execute(specimens.insert().values(specimen_id="SP", extra={}))
        await conn.execute(blocks.insert().values(block_id="B", specimen_id="SP", extra={}))
        await conn.execute(
            cutting_sessions.insert().values(
                cutting_session_id="CS",
                specimen_id="SP",
                block_id="B",
                start_time=pickup,
                sectioning_device="prototome",
                media_type="grid_disc",
                extra={},
            )
        )
        await conn.execute(layouts.insert().values(layout_id="L", media_type="grid_disc", extra={}))
        await conn.execute(
            substrates.insert().values(
                media_id="001123", substrate_layout_id="L", aperture_status=["used", "used", "used"], extra={}
            )
        )
        placements = {
            2: (0, pickup - timedelta(minutes=10)),
            8: (0, pickup - timedelta(minutes=10)),
            5: (2, pickup),
            6: (2, pickup),
            10: (2, pickup),
            11: (1, pickup + timedelta(minutes=1)),
        }
        for number, (aperture, timestamp) in placements.items():
            await conn.execute(
                sections.insert().values(
                    section_id=f"001123_S{number}",
                    section_number=number,
                    timestamp=timestamp,
                    cutting_session_id="CS",
                    block_id="B",
                    specimen_id="SP",
                    media_id="001123",
                    aperture_index=aperture,
                    extra={},
                )
            )
        if roi_on:
            await conn.execute(
                rois.insert().values(
                    roi_id="R1",
                    roi_number=1,
                    section_id=roi_on,
                    block_id="B",
                    specimen_id="SP",
                    substrate_media_id="001123",
                    hierarchy_level=0,
                    extra={},
                )
            )
    await engine.dispose()


async def section_ids(database_url: str) -> list[str]:
    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        ids = (await conn.execute(sa.select(sections.c.section_id).order_by(sections.c.section_id))).scalars().all()
    await engine.dispose()
    return list(ids)


async def test_upgrade_keeps_highest_numbered_duplicate(fresh_database_url):
    assert _run_alembic(fresh_database_url, "upgrade", "d5e6f7a8b9c0").returncode == 0
    await seed_overwritten_groups(fresh_database_url)

    result = _run_alembic(fresh_database_url, "upgrade", "head")

    assert result.returncode == 0, result.stderr
    assert await section_ids(fresh_database_url) == ["001123_S10", "001123_S11", "001123_S8"]


async def test_upgrade_stops_if_duplicate_has_roi(fresh_database_url):
    assert _run_alembic(fresh_database_url, "upgrade", "d5e6f7a8b9c0").returncode == 0
    await seed_overwritten_groups(fresh_database_url, roi_on="001123_S6")

    result = _run_alembic(fresh_database_url, "upgrade", "head")

    assert result.returncode != 0
    assert "001123_S6" in result.stderr
    assert len(await section_ids(fresh_database_url)) == 6
