import logging
import time
from datetime import datetime, timezone

import pymongo
import pytest
from beanie import init_beanie
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient

from temdb.main import create_app
from temdb.models.v1.grids import Grid
from temdb.models.v2.acquisition import Acquisition
from temdb.models.v2.block import Block
from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.enum_schemas import AcquisitionTaskStatus, MediaType
from temdb.models.v2.roi import ROI
from temdb.models.v2.section import Section
from temdb.models.v2.specimen import Specimen
from temdb.models.v2.task import AcquisitionTask
from temdb.models.v2.tile import Tile

logging.basicConfig(level=logging.INFO)

DATABASE_URL = "mongodb://localhost:27017/testdb"


@pytest.fixture(scope="function")
async def mongo_client():
    """Create a MongoDB client - function scoped to avoid event loop issues."""
    logging.info(f"Connecting to database: {DATABASE_URL}")
    retries = 5

    for i in range(retries):
        try:
            client = AsyncIOMotorClient(DATABASE_URL)
            await client.admin.command("ping")
            logging.info("Connected to database")
            yield client
            client.close()
            break
        except pymongo.errors.ConnectionFailure as e:
            logging.info(f"MongoDB not ready yet: {str(e)}, retrying...")
            time.sleep(5)
    else:
        logging.error("Could not connect to MongoDB after several retries")
        pytest.fail("MongoDB did not start in time")


@pytest.fixture(scope="function")
async def init_db(mongo_client: AsyncIOMotorClient):
    """Initialize the database - function scoped for test isolation."""
    db = mongo_client.get_database("testdb")
    await init_beanie(
        database=db,
        document_models=[
            Acquisition,
            Tile,
            ROI,
            AcquisitionTask,
            Specimen,
            Block,
            CuttingSession,
            Section,
            Grid,
        ],
    )
    yield db
    for collection in await db.list_collection_names():
        await db[collection].delete_many({})


@pytest.fixture
def app(init_db) -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_specimen():
    specimen = Specimen(
        specimen_id="TEST_SPECIMEN_001",
        description="Test specimen for API tests",
        created_at=datetime.now(timezone.utc),
    )
    await specimen.insert()
    yield specimen
    await specimen.delete()


@pytest.fixture
async def test_block(test_specimen):
    block = Block(
        block_id="TEST_BLOCK_001",
        specimen_id=test_specimen.id,
        microCT_info={"resolution": 1.5},
    )
    await block.insert()
    yield block
    await block.delete()


@pytest.fixture
async def test_cutting_session(test_specimen, test_block):
    cutting_session = CuttingSession(
        cutting_session_id="TEST_CUT_001",
        start_time=datetime.now(timezone.utc),
        operator="Test Operator",
        sectioning_device="Test Device",
        media_type=MediaType.TAPE,
        specimen_id=test_specimen.id,
        block_id=test_block.id,
    )
    await cutting_session.insert()
    yield cutting_session
    await cutting_session.delete()


@pytest.fixture
async def test_section(test_cutting_session):
    section = Section(
        section_id="TEST_SECTION_001",
        section_number=1,
        media_type=MediaType.TAPE,
        media_id="TEST_MEDIA_001",
        cutting_session_id=test_cutting_session.id,
    )
    await section.insert()
    yield section
    await section.delete()


@pytest.fixture
async def test_roi(test_section):
    roi = ROI(
        roi_id=1001,
        specimen_id="TEST_SPECIMEN_001",
        block_id="TEST_BLOCK_001",
        section_number=test_section.section_number,
        parent_roi_id=None,
    )
    await roi.insert()
    yield roi
    await roi.delete()


@pytest.fixture
async def test_acquisition_task(test_specimen, test_block, test_roi):
    acquisition_task = AcquisitionTask(
        task_id="TEST_TASK_001",
        task_type="standard_acquisition",
        version=1,
        specimen_id=test_specimen.id,
        block_id=test_block.id,
        roi_id=test_roi.id,
        status=AcquisitionTaskStatus.PLANNED,
        created_at=datetime.now(timezone.utc),
    )
    await acquisition_task.insert()
    yield acquisition_task
    await acquisition_task.delete()


@pytest.fixture
async def test_acquisition(test_specimen, test_roi, test_acquisition_task):
    acquisition = Acquisition(
        acquisition_id="TEST_ACQ_001",
        montage_id="TEST_MONTAGE_001",
        specimen_id=test_specimen.id,
        roi_id=test_roi.id,
        acquisition_task_id=test_acquisition_task.id,
        hardware_settings={
            "scope_id": "TEST_SCOPE_001",
            "camera_model": "Test Camera",
            "camera_serial": "12345",
            "camera_bit_depth": 16,
            "media_type": MediaType.TAPE,
        },
        acquisition_settings={
            "magnification": 1000,
            "spot_size": 2,
            "exposure_time": 100,
            "tile_size": [4096, 4096],
            "tile_overlap": 0.1,
            "saved_bit_depth": 8,
        },
        start_time=datetime.now(timezone.utc),
    )
    await acquisition.insert()
    yield acquisition
    await acquisition.delete()


@pytest.fixture
async def test_tile(test_acquisition):
    tile = Tile(
        tile_id="TEST_TILE_001",
        acquisition_id=test_acquisition.id,
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
    await tile.delete()
