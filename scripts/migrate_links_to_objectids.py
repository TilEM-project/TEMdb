"""Normalise TEMdb ref fields to bare ObjectId, and drop pre-L1 indexes.

Usage:
    uv run python -m scripts.migrate_links_to_objectids \
        --mongo-url "$MONGO_URL" --db temdb --dry-run

Two steps:
  1. Rewrite every ref field whose value is a Beanie Link wrapper or DBRef
     into a bare ObjectId (idempotent for already-bare values).
  2. Drop any index whose key path contains "_ref.id" (the pre-L1 shape).
     Beanie will recreate the new `_ref`-keyed indexes on next startup.
     Required before deploying L1 code against an existing cluster — Mongo
     refuses to replace an index with the same name but different key spec.
"""

import argparse
import asyncio
import logging
from typing import Any

from bson import DBRef, ObjectId
from pymongo import AsyncMongoClient

logger = logging.getLogger(__name__)


COLLECTIONS_AND_REFS: list[tuple[str, list[str]]] = [
    ("blocks", ["specimen_ref"]),
    ("cutting_sessions", ["specimen_ref", "block_ref"]),
    ("sections", ["cutting_session_ref", "substrate_ref"]),
    ("rois", ["section_ref", "parent_roi_ref"]),
    ("acquisition_tasks", ["specimen_ref", "block_ref", "roi_ref"]),
    ("acquisitions", ["specimen_ref", "roi_ref", "acquisition_task_ref"]),
    ("tiles", ["acquisition_ref"]),
]


def _coerce(value: Any) -> ObjectId | None:
    """Return a bare ObjectId, or None if already bare / unmigrateable."""
    if value is None or isinstance(value, ObjectId):
        return None
    if isinstance(value, DBRef):
        return value.id if isinstance(value.id, ObjectId) else ObjectId(value.id)
    if isinstance(value, dict):
        if "id" in value and isinstance(value["id"], ObjectId):
            return value["id"]
        if "$id" in value:
            return (
                value["$id"]
                if isinstance(value["$id"], ObjectId)
                else ObjectId(value["$id"])
            )
    raise ValueError(f"Unrecognised ref shape: {value!r}")


async def migrate_database(
    db, *, dry_run: bool
) -> dict[str, dict[str, dict[str, int]]]:
    summary: dict[str, dict[str, dict[str, int]]] = {}

    for coll_name, fields in COLLECTIONS_AND_REFS:
        coll = db[coll_name]
        summary[coll_name] = {}

        for field in fields:
            scanned = migrated = would = errors = 0
            cursor = coll.find({field: {"$exists": True, "$ne": None}})
            async for doc in cursor:
                scanned += 1
                try:
                    new_value = _coerce(doc[field])
                except ValueError as exc:
                    errors += 1
                    logger.error("%s/%s _id=%s: %s", coll_name, field, doc["_id"], exc)
                    continue
                if new_value is None:
                    continue
                if dry_run:
                    would += 1
                    continue
                await coll.update_one({"_id": doc["_id"]}, {"$set": {field: new_value}})
                migrated += 1

            summary[coll_name][field] = {
                "scanned": scanned,
                "migrated": migrated,
                "would_migrate": would,
                "errors": errors,
            }
            logger.info("%s/%s: %s", coll_name, field, summary[coll_name][field])
    return summary


async def drop_legacy_ref_indexes(db, *, dry_run: bool) -> dict[str, list[str]]:
    """Drop any index whose key path contains `_ref.id` (pre-L1 shape)."""
    dropped: dict[str, list[str]] = {}
    for coll_name, _fields in COLLECTIONS_AND_REFS:
        coll = db[coll_name]
        dropped[coll_name] = []
        cursor = await coll.list_indexes()
        async for idx in cursor:
            key_paths = list(idx.get("key", {}).keys())
            if not any("_ref.id" in p for p in key_paths):
                continue
            name = idx["name"]
            logger.info(
                "%s: %s index %r (key=%s)",
                coll_name,
                "would drop" if dry_run else "dropping",
                name,
                key_paths,
            )
            if not dry_run:
                await coll.drop_index(name)
            dropped[coll_name].append(name)
    return dropped


async def _main_async(args) -> int:
    client = AsyncMongoClient(args.mongo_url)
    try:
        db = client[args.db]
        summary = await migrate_database(db, dry_run=args.dry_run)
        dropped = await drop_legacy_ref_indexes(db, dry_run=args.dry_run)
    finally:
        await client.close()

    total_errors = sum(
        per_field["errors"]
        for per_coll in summary.values()
        for per_field in per_coll.values()
    )
    total_dropped = sum(len(v) for v in dropped.values())
    logger.info(
        "Index summary: %d legacy `_ref.id` indexes %s",
        total_dropped,
        "would be dropped" if args.dry_run else "dropped",
    )
    return 1 if total_errors else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mongo-url", required=True)
    p.add_argument("--db", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args()
    logging.basicConfig(
        level=args.log_level, format="%(levelname)s %(name)s: %(message)s"
    )
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
