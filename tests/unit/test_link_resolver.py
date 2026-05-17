import pytest
from beanie import init_beanie
from beanie.odm.fields import PydanticObjectId
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
from temdb.server.link_resolver import resolve_links

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
