import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

# size_class -> hash subpartition modulus. Target ~25-50M rows per leaf
# partition across the plausible dataset-size range. See the design spec.
SIZE_CLASS_MODULUS: dict[str, int] = {
    "small": 4,      # <= ~100M tiles
    "medium": 32,    # <= ~1B tiles
    "large": 256,    # <= ~10B tiles
    "xlarge": 1024,  # <= ~50B tiles
}


# Upper tile-count bound per size_class; resolve_size_class picks the smallest
# class whose ceiling is not exceeded. Anything above 'large' -> 'xlarge'.
SIZE_CLASS_CEILING: dict[str, int] = {
    "small": 100_000_000,        # <= 100M
    "medium": 1_000_000_000,     # <= 1B
    "large": 10_000_000_000,     # <= 10B
}


def resolve_size_class(estimated_tile_count: int) -> str:
    """Pick the size_class for an estimated tile count."""
    if estimated_tile_count < 0:
        raise ValueError("estimated_tile_count must be non-negative")
    for size_class, ceiling in SIZE_CLASS_CEILING.items():
        if estimated_tile_count <= ceiling:
            return size_class
    return "xlarge"


def resolve_modulus(size_class: str) -> int:
    """Map a dataset size_class to its hash subpartition modulus."""
    try:
        return SIZE_CLASS_MODULUS[size_class]
    except KeyError:
        raise ValueError(
            f"Unknown size_class {size_class!r}; expected one of {sorted(SIZE_CLASS_MODULUS)}"
        )


def partition_name(dataset_id: uuid.UUID) -> str:
    """Deterministic name of a dataset's top-level LIST partition.

    `dataset_id.hex` is 32 hex chars with no metacharacters, so it is safe to
    interpolate into DDL.
    """
    return f"tile_d_{dataset_id.hex}"


def lock_key(dataset_id: uuid.UUID) -> int:
    """Stable signed 64-bit advisory-lock key derived from the dataset UUID."""
    return int.from_bytes(dataset_id.bytes[:8], "big", signed=True)


async def _resolve_and_freeze_modulus(session: AsyncSession, dataset_id: uuid.UUID) -> int:
    """Return the dataset's frozen hash modulus, computing+freezing it once.

    Runs under the caller's advisory lock so the read-modify-write is safe.
    """
    row = (
        await session.execute(
            text("SELECT tile_hash_modulus, size_class FROM datasets WHERE dataset_id = :id FOR UPDATE"),
            {"id": dataset_id},
        )
    ).one_or_none()
    if row is None:
        raise ValueError(f"Dataset {dataset_id} does not exist")
    modulus, size_class = row
    if modulus is None:
        modulus = resolve_modulus(size_class)
        await session.execute(
            text("UPDATE datasets SET tile_hash_modulus = :m WHERE dataset_id = :id"),
            {"m": modulus, "id": dataset_id},
        )
    return int(modulus)


async def partition_exists(session: AsyncSession, dataset_id: uuid.UUID) -> bool:
    """True if the dataset's tile partition has already been created.

    Uses Postgres `to_regclass`, which returns the relation's OID or NULL
    (and does NOT raise) when the table is absent — the cheap existence check.
    """
    oid = (await session.execute(
        text("SELECT to_regclass(:n)"), {"n": partition_name(dataset_id)}
    )).scalar()
    return oid is not None


async def ensure_tile_partition(session: AsyncSession, dataset_id: uuid.UUID) -> None:
    """Create the LIST partition (and its HASH children) for a dataset.

    Idempotent. Call before inserting any tile row for the dataset. A
    transaction-scoped advisory lock serializes partition creation per dataset
    so concurrent writers cannot race the non-atomic CREATE ... IF NOT EXISTS.
    """
    if await partition_exists(session, dataset_id):
        return  # fast path: partition (and its hash children) already created
    await session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": lock_key(dataset_id)})
    modulus = await _resolve_and_freeze_modulus(session, dataset_id)
    name = partition_name(dataset_id)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {name} PARTITION OF tiles "
        f"FOR VALUES IN ('{dataset_id}') PARTITION BY HASH (run_id)"
    ))
    for i in range(modulus):
        await session.execute(text(
            f"CREATE TABLE IF NOT EXISTS {name}_h{i} PARTITION OF {name} "
            f"FOR VALUES WITH (MODULUS {modulus}, REMAINDER {i})"
        ))


async def drop_tile_partition(engine: AsyncEngine, dataset_id: uuid.UUID) -> None:
    """Drop a dataset's tile partition subtree (archival). Idempotent.

    DETACH CONCURRENTLY (ShareUpdateExclusive on the parent) instead of a direct
    DROP (AccessExclusive on the parent), so concurrent ingest into other
    datasets' partitions is never blocked or deadlocked.

    DETACH CONCURRENTLY runs in two transactions; a crash between them leaves
    pg_inherits.inhdetachpending=true and the partition needs DETACH ... FINALIZE
    before it can be dropped. Three states handled: attached (detach + drop),
    detach-pending (finalize + drop), detached-but-not-dropped (drop).
    CONCURRENTLY cannot run in a transaction block, hence AUTOCOMMIT on a
    dedicated connection. Invariant: `tiles` never has a DEFAULT partition
    (CONCURRENTLY is unsupported with one).
    """
    name = partition_name(dataset_id)
    async with engine.connect() as conn:
        ac = await conn.execution_options(isolation_level="AUTOCOMMIT")
        exists = (await ac.execute(text("SELECT to_regclass(:n)"), {"n": name})).scalar()
        if exists is None:
            return
        pending = (await ac.execute(text(
            "SELECT inhdetachpending FROM pg_inherits WHERE inhrelid = to_regclass(:n)"
        ), {"n": name})).scalar()  # None = no longer attached to the parent
        if pending is True:
            await ac.execute(text(f"ALTER TABLE tiles DETACH PARTITION {name} FINALIZE"))
        elif pending is False:
            await ac.execute(text(f"ALTER TABLE tiles DETACH PARTITION {name} CONCURRENTLY"))
        await ac.execute(text(f"DROP TABLE IF EXISTS {name}"))
