import logging
from datetime import datetime, timezone

import pytest
from beanie import init_beanie
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from pymongo import AsyncMongoClient
from testcontainers.mongodb import MongoDbContainer

from temdb.database import DatabaseManager
from temdb.dependencies import get_db_manager
from temdb.main import create_app
from temdb.models.v1.grids import Grid
from temdb.models.v2.acquisition import Acquisition
from temdb.models.v2.block import Block
from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.enum_schemas import AcquisitionStatus, AcquisitionTaskStatus
from temdb.models.v2.roi import ROI
from temdb.models.v2.section import Section
from temdb.models.v2.specimen import Specimen
from temdb.models.v2.substrate import Substrate
from temdb.models.v2.task import AcquisitionTask
from temdb.models.v2.tile import Tile

logging.basicConfig(level=logging.INFO)

TEST_DB_NAME = "testdb"

DOCUMENT_MODELS = [
    Acquisition,
    Tile,
    ROI,
    AcquisitionTask,
    Specimen,
    Block,
    CuttingSession,
    Section,
    Substrate,
    Grid,
]


@pytest.fixture(scope="session")
def mongo_container():
    """Start MongoDB container once per test session."""
    with MongoDbContainer("mongo:8") as container:
        yield container


@pytest.fixture(scope="function")
async def mongo_client(mongo_container):
    """Create a MongoDB client using the testcontainer."""
    connection_url = mongo_container.get_connection_url()
    client = AsyncMongoClient(connection_url)
    yield client
    await client.close()


@pytest.fixture(scope="function")
async def mongo_client_session(mongo_client):
    """Create a session using the shared client."""
    yield mongo_client


@pytest.fixture(scope="function")
async def test_db_manager(mongo_container, mongo_client_session, init_db):
    """Create DatabaseManager using the SAME client as Beanie."""
    db_manager = DatabaseManager(
        mongodb_uri=mongo_container.get_connection_url(), mongodb_name=TEST_DB_NAME
    )
    db_manager.client = mongo_client_session
    db_manager.db = mongo_client_session[TEST_DB_NAME]

    yield db_manager


@pytest.fixture(scope="function")
async def init_db(mongo_client_session):
    """Initialize Beanie with the shared client."""
    db = mongo_client_session[TEST_DB_NAME]

    collections = await db.list_collection_names()
    for collection_name in collections:
        if not collection_name.startswith("system."):
            await db[collection_name].delete_many({})

    await init_beanie(
        database=db,
        document_models=DOCUMENT_MODELS,
    )
    yield db


@pytest.fixture(scope="function")
def app(test_db_manager: DatabaseManager, init_db) -> FastAPI:
    """Create FastAPI app instance for testing with dependency override."""
    app_instance = create_app()

    app_instance.dependency_overrides[get_db_manager] = lambda: test_db_manager

    yield app_instance

    app_instance.dependency_overrides = {}


@pytest.fixture(scope="function")
async def async_client(app: FastAPI) -> AsyncClient:
    """Asynchronous TestClient using the overridden app."""
    async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as client:
        yield client


@pytest.fixture(scope="function")
async def test_specimen(init_db):
    """Creates a test Specimen document."""
    specimen = Specimen(
        specimen_id="TEST_SPECIMEN_001",
        description="Test specimen for API tests",
        created_at=datetime.now(timezone.utc),
    )
    await specimen.insert()
    yield specimen


@pytest.fixture(scope="function")
async def test_block(init_db, test_specimen: Specimen):
    """Creates a test Block document linked to test_specimen."""
    block = Block(
        block_id="TEST_BLOCK_001",
        specimen_id=test_specimen.specimen_id,
        specimen_ref=test_specimen.id,
        microCT_info={"resolution": 1.5},
    )
    await block.insert()
    yield block


@pytest.fixture(scope="function")
async def test_cutting_session(init_db, test_specimen: Specimen, test_block: Block):
    """Creates a test CuttingSession document linked to test_block."""
    cutting_session = CuttingSession(
        cutting_session_id="TEST_CUT_001",
        specimen_id=test_specimen.specimen_id,
        block_id=test_block.block_id,
        specimen_ref=test_specimen.id,
        block_ref=test_block.id,
        start_time=datetime.now(timezone.utc),
        operator="Test Operator",
        sectioning_device="Test Device",
        media_type="tape",
    )
    await cutting_session.insert()
    yield cutting_session


@pytest.fixture(scope="function")
async def test_substrate(init_db):
    """Creates a test Substrate document."""
    substrate = Substrate(
        media_id="TEST_MEDIA_001",
        media_type="tape",
        substrate_id="TEST_SUBSTRATE_001",
        description="Test substrate for API tests",
        created_at=datetime.now(timezone.utc),
    )
    await substrate.insert()
    yield substrate

@pytest.fixture(scope="function")
async def test_section(init_db, test_cutting_session: CuttingSession, test_substrate: Substrate):
    """Creates a test Section document linked to test_cutting_session."""
    section = Section(
        section_id="TEST_SECTION_001",
        section_number=1,
        timestamp=datetime.now(timezone.utc),
        cutting_session_id=test_cutting_session.cutting_session_id,
        block_id=test_cutting_session.block_id,
        specimen_id=test_cutting_session.specimen_id,
        cutting_session_ref=test_cutting_session.id,
        substrate_ref=test_substrate.id,
        media_type="tape",
        media_id="TEST_MEDIA_001",
    )
    await section.insert()
    yield section


@pytest.fixture(scope="function")
async def test_roi(init_db, test_section: Section):
    """Creates a test ROI document linked to test_section."""
    roi = ROI(
        roi_id="SPEC001.BLK001.CS001.SEC001.SUB001.ROI001",
        roi_number=1,
        section_id=test_section.section_id,
        block_id=test_section.block_id,
        specimen_id=test_section.specimen_id,
        substrate_media_id="SUB001",
        hierarchy_level=1,
        section_ref=test_section.id,
        parent_roi_ref=None,
        updated_at=datetime.now(timezone.utc),
        section_number=test_section.section_number,
    )
    await roi.insert()
    yield roi


@pytest.fixture(scope="function")
async def test_acquisition_task(
    init_db, test_specimen: Specimen, test_block: Block, test_roi: ROI
):
    """Creates a test AcquisitionTask document linked to Specimen, Block, and ROI."""
    acquisition_task = AcquisitionTask(
        task_id="TEST_TASK_001",
        specimen_id=test_specimen.specimen_id,
        block_id=test_block.block_id,
        roi_id=test_roi.roi_id,
        specimen_ref=test_specimen.id,
        block_ref=test_block.id,
        roi_ref=test_roi.id,
        task_type="standard_acquisition",
        version=1,
        status=AcquisitionTaskStatus.PLANNED,
        created_at=datetime.now(timezone.utc),
    )
    await acquisition_task.insert()
    yield acquisition_task


@pytest.fixture(scope="function")
async def test_acquisition(
    init_db,
    test_specimen: Specimen,
    test_roi: ROI,
    test_acquisition_task: AcquisitionTask,
):
    """Creates a test Acquisition document linked to Specimen, ROI, and Task."""
    acquisition = Acquisition(
        acquisition_id="TEST_ACQ_001",
        montage_id="TEST_MONTAGE_001",
        specimen_id=test_specimen.specimen_id,
        roi_id=test_roi.roi_id,
        acquisition_task_id=test_acquisition_task.task_id,
        specimen_ref=test_specimen.id,
        roi_ref=test_roi.id,
        acquisition_task_ref=test_acquisition_task.id,
        hardware_settings={
            "scope_id": "TEST_SCOPE_001",
            "camera_model": "Test Camera",
            "camera_serial": "12345",
            "camera_bit_depth": 16,
            "media_type": "tape",
        },
        acquisition_settings={
            "magnification": 1000,
            "spot_size": 2,
            "exposure_time": 100,
            "tile_size": [4096, 4096],
            "tile_overlap": 0.1,
            "saved_bit_depth": 8,
        },
        status=AcquisitionStatus.IMAGING,
        start_time=datetime.now(timezone.utc),
    )
    await acquisition.insert()
    yield acquisition


@pytest.fixture(scope="function")
async def test_tile(init_db, test_acquisition: Acquisition):
    """Creates a test Tile document linked to test_acquisition."""
    tile = Tile(
        tile_id="TEST_TILE_001",
        acquisition_id=test_acquisition.acquisition_id,
        acquisition_ref=test_acquisition.id,
        raster_index=1,
        stage_position={"x": 100, "y": 200},
        raster_position={"row": 0, "col": 0},
        focus_score=0.95,
        min_value=0,
        max_value=255,
        mean_value=128,
        std_value=25,
        image_path="/path/to/test/image.tif",
    )
    await tile.insert()
    yield tile
