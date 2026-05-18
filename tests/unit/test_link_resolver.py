from datetime import datetime, timezone

import pytest
from beanie import init_beanie
from beanie.odm.fields import PydanticObjectId
from bson import ObjectId
from pymongo import AsyncMongoClient
from testcontainers.mongodb import MongoDbContainer

from temdb.server.documents import (
    AcquisitionDocument,
    AcquisitionTaskDocument,
    BlockDocument,
    CuttingSessionDocument,
    ROIDocument,
    SectionDocument,
    SpecimenDocument,
    SubstrateDocument,
    TileDocument,
)
from temdb.server.link_resolver import resolve_links, resolve_links_recursive

DOCUMENT_MODELS = [
    SpecimenDocument, BlockDocument, CuttingSessionDocument, SectionDocument,
    ROIDocument, AcquisitionTaskDocument, AcquisitionDocument, TileDocument,
    SubstrateDocument,
]


@pytest.fixture(scope="module")
def mongo_container():
    with MongoDbContainer("mongo:8") as c:
        yield c


@pytest.fixture
async def db(mongo_container):
    client = AsyncMongoClient(mongo_container.get_connection_url())
    database = client["link_resolver_test"]
    for name in await database.list_collection_names():
        await database[name].delete_many({})
    await init_beanie(database=database, document_models=DOCUMENT_MODELS)
    yield database
    await client.close()


async def test_resolve_links_single_doc_single_field(db):
    specimen = await SpecimenDocument(specimen_id="SPEC001").insert()
    block = await BlockDocument(
        block_id="BLK001",
        specimen_id="SPEC001",
        specimen_ref=specimen.id,
    ).insert()

    registry = await resolve_links(block, [("specimen_ref", SpecimenDocument)])

    assert "specimen_ref" in registry
    assert specimen.id in registry["specimen_ref"]
    assert registry["specimen_ref"][specimen.id].specimen_id == "SPEC001"


async def test_resolve_links_list_of_docs_batches_one_query_per_field(db, monkeypatch):
    specimen_a = await SpecimenDocument(specimen_id="SPEC_A").insert()
    specimen_b = await SpecimenDocument(specimen_id="SPEC_B").insert()
    block_a1 = await BlockDocument(block_id="BLK_A1", specimen_id="SPEC_A", specimen_ref=specimen_a.id).insert()
    block_a2 = await BlockDocument(block_id="BLK_A2", specimen_id="SPEC_A", specimen_ref=specimen_a.id).insert()
    block_b1 = await BlockDocument(block_id="BLK_B1", specimen_id="SPEC_B", specimen_ref=specimen_b.id).insert()

    call_count = {"n": 0}
    original_find = SpecimenDocument.find

    def counting_find(*args, **kwargs):
        call_count["n"] += 1
        return original_find(*args, **kwargs)

    monkeypatch.setattr(SpecimenDocument, "find", counting_find)

    registry = await resolve_links(
        [block_a1, block_a2, block_b1],
        [("specimen_ref", SpecimenDocument)],
    )

    assert call_count["n"] == 1
    assert set(registry["specimen_ref"].keys()) == {specimen_a.id, specimen_b.id}


async def test_resolve_links_nullable_field_returns_empty(db):
    specimen = await SpecimenDocument(specimen_id="SPEC1").insert()
    block = await BlockDocument(block_id="BLK1", specimen_id="SPEC1", specimen_ref=specimen.id).insert()
    cs = await CuttingSessionDocument(
        cutting_session_id="CS1", specimen_id="SPEC1", block_id="BLK1",
        start_time=datetime.now(timezone.utc),
        sectioning_device="dev", media_type="wafer",
        specimen_ref=specimen.id, block_ref=block.id,
    ).insert()
    substrate = await SubstrateDocument(media_id="MED1", media_type="wafer").insert()
    section = await SectionDocument(
        section_id="SEC1", section_number=1,
        cutting_session_id="CS1", block_id="BLK1", specimen_id="SPEC1", media_id="MED1",
        cutting_session_ref=cs.id, substrate_ref=substrate.id,
    ).insert()
    roi = await ROIDocument(
        roi_id="SPEC1.BLK1.SEC1.MED1.ROI001",
        roi_number=1, section_id="SEC1", block_id="BLK1", specimen_id="SPEC1",
        substrate_media_id="MED1", hierarchy_level=1,
        section_ref=section.id, parent_roi_ref=None,
    ).insert()

    registry = await resolve_links(
        roi,
        [("parent_roi_ref", ROIDocument), ("section_ref", SectionDocument)],
    )

    assert registry["parent_roi_ref"] == {}
    assert section.id in registry["section_ref"]


async def test_resolve_links_handles_none_input(db):
    registry = await resolve_links(None, [("specimen_ref", SpecimenDocument)])
    assert registry == {"specimen_ref": {}}


async def test_resolve_links_missing_target_absent_from_registry(db):
    # Ref points to an ObjectId that has no matching SpecimenDocument.
    dangling_id = PydanticObjectId(ObjectId())
    block = await BlockDocument(
        block_id="DANGLING", specimen_id="GHOST", specimen_ref=dangling_id,
    ).insert()

    registry = await resolve_links(block, [("specimen_ref", SpecimenDocument)])

    assert registry["specimen_ref"] == {}
    assert dangling_id not in registry["specimen_ref"]


async def test_resolve_links_recursive_two_levels(db):
    specimen = await SpecimenDocument(specimen_id="SPEC1").insert()
    block = await BlockDocument(block_id="BLK1", specimen_id="SPEC1", specimen_ref=specimen.id).insert()
    cs = await CuttingSessionDocument(
        cutting_session_id="CS1", specimen_id="SPEC1", block_id="BLK1",
        start_time=datetime.now(timezone.utc),
        sectioning_device="dev", media_type="wafer",
        specimen_ref=specimen.id, block_ref=block.id,
    ).insert()
    substrate = await SubstrateDocument(media_id="MED1", media_type="wafer").insert()
    section = await SectionDocument(
        section_id="SEC1", section_number=1,
        cutting_session_id="CS1", block_id="BLK1", specimen_id="SPEC1", media_id="MED1",
        cutting_session_ref=cs.id, substrate_ref=substrate.id,
    ).insert()

    plan = {
        "cutting_session_ref": (CuttingSessionDocument, {
            "specimen_ref": (SpecimenDocument, {}),
            "block_ref": (BlockDocument, {}),
        }),
        "substrate_ref": (SubstrateDocument, {}),
    }

    registry = await resolve_links_recursive([section], plan)

    assert cs.id in registry["cutting_session_ref"]
    assert specimen.id in registry["cutting_session_ref.specimen_ref"]
    assert block.id in registry["cutting_session_ref.block_ref"]
    assert substrate.id in registry["substrate_ref"]
