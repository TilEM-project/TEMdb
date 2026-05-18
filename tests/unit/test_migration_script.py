import pytest
from bson import DBRef, ObjectId
from pymongo import AsyncMongoClient
from testcontainers.mongodb import MongoDbContainer

from scripts.migrate_links_to_objectids import drop_legacy_ref_indexes


@pytest.fixture(scope="module")
def mongo_container():
    with MongoDbContainer("mongo:8") as c:
        yield c


@pytest.fixture
async def db(mongo_container):
    client = AsyncMongoClient(mongo_container.get_connection_url())
    database = client["migration_test"]
    for name in await database.list_collection_names():
        await database[name].delete_many({})
    yield database
    await client.close()


async def test_migrates_beanie_link_shape(db):
    from scripts.migrate_links_to_objectids import migrate_database

    spec_id = ObjectId()
    block_id = ObjectId()
    await db.specimens.insert_one({"_id": spec_id, "specimen_id": "SPEC1"})
    await db.blocks.insert_one(
        {
            "_id": block_id,
            "block_id": "BLK1",
            "specimen_id": "SPEC1",
            "specimen_ref": {"id": spec_id, "collection": "specimens"},
        }
    )

    summary = await migrate_database(db, dry_run=False)

    block = await db.blocks.find_one({"_id": block_id})
    assert block["specimen_ref"] == spec_id
    assert summary["blocks"]["specimen_ref"]["migrated"] == 1


async def test_migrates_legacy_dbref_shape(db):
    from scripts.migrate_links_to_objectids import migrate_database

    spec_id = ObjectId()
    block_id = ObjectId()
    await db.specimens.insert_one({"_id": spec_id, "specimen_id": "SPEC1"})
    await db.blocks.insert_one(
        {
            "_id": block_id,
            "block_id": "BLK1",
            "specimen_id": "SPEC1",
            "specimen_ref": DBRef("specimens", spec_id),
        }
    )

    await migrate_database(db, dry_run=False)

    block = await db.blocks.find_one({"_id": block_id})
    assert block["specimen_ref"] == spec_id


async def test_idempotent_on_bare_objectid(db):
    from scripts.migrate_links_to_objectids import migrate_database

    spec_id = ObjectId()
    block_id = ObjectId()
    await db.specimens.insert_one({"_id": spec_id, "specimen_id": "SPEC1"})
    await db.blocks.insert_one(
        {
            "_id": block_id,
            "block_id": "BLK1",
            "specimen_id": "SPEC1",
            "specimen_ref": spec_id,
        }
    )

    summary = await migrate_database(db, dry_run=False)

    block = await db.blocks.find_one({"_id": block_id})
    assert block["specimen_ref"] == spec_id
    assert summary["blocks"]["specimen_ref"]["migrated"] == 0


async def test_dry_run_does_not_write(db):
    from scripts.migrate_links_to_objectids import migrate_database

    spec_id = ObjectId()
    block_id = ObjectId()
    await db.specimens.insert_one({"_id": spec_id, "specimen_id": "SPEC1"})
    await db.blocks.insert_one(
        {
            "_id": block_id,
            "block_id": "BLK1",
            "specimen_id": "SPEC1",
            "specimen_ref": {"id": spec_id, "collection": "specimens"},
        }
    )

    summary = await migrate_database(db, dry_run=True)

    block = await db.blocks.find_one({"_id": block_id})
    assert isinstance(block["specimen_ref"], dict)
    assert summary["blocks"]["specimen_ref"]["would_migrate"] == 1


async def test_drops_legacy_ref_id_indexes(db):

    await db.blocks.create_index([("specimen_ref.id", 1)], name="specimen_ref_index")
    await db.acquisitions.create_index(
        [("roi_ref.id", 1), ("start_time", -1)], name="roi_ref_start_time_index"
    )
    # An index whose key has no `_ref.id` must be left alone:
    await db.blocks.create_index([("created_at", -1)], name="created_at_index")

    dropped = await drop_legacy_ref_indexes(db, dry_run=False)

    assert "specimen_ref_index" in dropped["blocks"]
    assert "roi_ref_start_time_index" in dropped["acquisitions"]
    assert "created_at_index" not in dropped["blocks"]

    remaining = [i["name"] async for i in (await db.blocks.list_indexes())]
    assert "specimen_ref_index" not in remaining
    assert "created_at_index" in remaining


async def test_drop_indexes_dry_run_does_not_drop(db):

    await db.blocks.create_index([("specimen_ref.id", 1)], name="specimen_ref_index")

    dropped = await drop_legacy_ref_indexes(db, dry_run=True)

    assert "specimen_ref_index" in dropped["blocks"]
    remaining = [i["name"] async for i in (await db.blocks.list_indexes())]
    assert "specimen_ref_index" in remaining  # dry-run did not actually drop
