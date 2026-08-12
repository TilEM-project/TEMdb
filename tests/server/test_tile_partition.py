import asyncio
import uuid as _uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from temdb.server.ids import uuid7
from temdb.server.sqlmodels import DatasetSQLModel
from temdb.server.sqlmodels.tile_partition import (
    drop_tile_partition,
    ensure_tile_partition,
    partition_name,
)


@pytest.mark.asyncio
async def test_tiles_is_partitioned_by_list(init_db, test_db_manager):
    async with test_db_manager.async_session_factory() as session:
        kind = (
            await session.execute(
                text("SELECT partstrat FROM pg_partitioned_table p "
                     "JOIN pg_class c ON c.oid = p.partrelid WHERE c.relname = 'tiles'")
            )
        ).scalar()
        # 'l' == LIST partitioning. asyncpg surfaces Postgres's internal
        # "char" type as a single-byte value, so normalize before comparing.
        if isinstance(kind, bytes):
            kind = kind.decode()
        assert kind == "l"


async def _make_dataset(session, size_class="small"):
    ds = DatasetSQLModel(
        dataset_id=uuid7(), name=f"ds_{uuid7().hex[:8]}", size_class=size_class,
        created_at=datetime.now(timezone.utc),
    )
    session.add(ds)
    await session.commit()
    return ds.dataset_id


async def _child_count(session, parent: str) -> int:
    return (
        await session.execute(
            text("SELECT count(*) FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhparent "
                 "WHERE c.relname = :p"),
            {"p": parent},
        )
    ).scalar()


@pytest.mark.asyncio
async def test_ensure_creates_nested_partitions_and_freezes_modulus(init_db, test_db_manager):
    async with test_db_manager.async_session_factory() as session:
        ds_id = await _make_dataset(session, size_class="small")  # modulus 4
        await ensure_tile_partition(session, ds_id)
        await session.commit()

        assert await _child_count(session, partition_name(ds_id)) == 4
        frozen = (
            await session.execute(
                text("SELECT tile_hash_modulus FROM datasets WHERE dataset_id = :id"), {"id": ds_id}
            )
        ).scalar()
        assert frozen == 4


@pytest.mark.asyncio
async def test_ensure_is_idempotent(init_db, test_db_manager):
    async with test_db_manager.async_session_factory() as session:
        ds_id = await _make_dataset(session, size_class="medium")  # modulus 32
        await ensure_tile_partition(session, ds_id)
        await session.commit()
        await ensure_tile_partition(session, ds_id)  # must not raise
        await session.commit()
        assert await _child_count(session, partition_name(ds_id)) == 32


async def _seed_partitioned_dataset(test_db_manager, size_class="small"):
    async with test_db_manager.async_session_factory() as session:
        ds_id = await _make_dataset(session, size_class=size_class)
        await ensure_tile_partition(session, ds_id)
        await session.commit()
    return ds_id


async def _partition_oid(engine, name):
    async with engine.connect() as conn:
        return (await conn.execute(text("SELECT to_regclass(:n)"), {"n": name})).scalar()


@pytest.mark.asyncio
async def test_drop_tile_partition_detaches_and_drops(init_db, test_db_manager):
    ds_id = await _seed_partitioned_dataset(test_db_manager)
    engine = test_db_manager.sql_engine
    await drop_tile_partition(engine, ds_id)
    assert await _partition_oid(engine, partition_name(ds_id)) is None


@pytest.mark.asyncio
async def test_drop_tile_partition_idempotent(init_db, test_db_manager):
    ds_id = await _seed_partitioned_dataset(test_db_manager)
    engine = test_db_manager.sql_engine
    await drop_tile_partition(engine, ds_id)
    await drop_tile_partition(engine, ds_id)  # second call: no-op, no error
    assert await _partition_oid(engine, partition_name(ds_id)) is None


@pytest.mark.asyncio
async def test_drop_recovers_detached_but_not_dropped(init_db, test_db_manager):
    # simulate a crash after detach, before drop
    ds_id = await _seed_partitioned_dataset(test_db_manager)
    engine = test_db_manager.sql_engine
    name = partition_name(ds_id)
    async with engine.connect() as conn:
        ac = await conn.execution_options(isolation_level="AUTOCOMMIT")
        await ac.execute(text(f"ALTER TABLE tiles DETACH PARTITION {name} CONCURRENTLY"))
    await drop_tile_partition(engine, ds_id)  # must finish the job
    assert await _partition_oid(engine, name) is None


@pytest.mark.asyncio
async def test_per_acquisition_read_prunes_to_one_child(init_db, test_db_manager):
    async with test_db_manager.async_session_factory() as session:
        ds_id = await _make_dataset(session, size_class="small")  # 4 children
        await ensure_tile_partition(session, ds_id)
        await session.commit()
        plan = (
            await session.execute(
                text(
                    "EXPLAIN (FORMAT TEXT) SELECT * FROM tiles "
                    "WHERE dataset_id = :d AND run_id = :a"
                ),
                {"d": ds_id, "a": uuid7()},
            )
        ).scalars().all()
        plan_text = "\n".join(plan)
        # Exactly one hash leaf partition is scanned (others pruned at plan time).
        scanned = [line for line in plan if "tile_d_" in line and "_h" in line]
        assert len(scanned) == 1, plan_text


@pytest.mark.asyncio
async def test_concurrent_ensure_does_not_error(init_db, test_db_manager):
    async def worker(ds_id):
        async with test_db_manager.async_session_factory() as session:
            await ensure_tile_partition(session, ds_id)
            await session.commit()

    async with test_db_manager.async_session_factory() as session:
        ds_id = await _make_dataset(session, size_class="small")

    await asyncio.gather(*(worker(ds_id) for _ in range(5)))

    async with test_db_manager.async_session_factory() as session:
        assert await _child_count(session, partition_name(ds_id)) == 4


@pytest.mark.asyncio
async def test_archival_drops_partition_and_sets_status(async_client, test_db_manager):
    created = (await async_client.post("/api/v2/datasets", json={"name": "ds_arch", "size_class": "small"})).json()
    ds_id = _uuid.UUID(created["dataset_id"])
    async with test_db_manager.async_session_factory() as session:
        await ensure_tile_partition(session, ds_id)
        await session.commit()

    patched = await async_client.patch(f"/api/v2/datasets/{created['dataset_id']}", json={"status": "archived"})
    assert patched.json()["archived_at"] is not None

    await drop_tile_partition(test_db_manager.sql_engine, ds_id)
    assert await _partition_oid(test_db_manager.sql_engine, partition_name(ds_id)) is None
