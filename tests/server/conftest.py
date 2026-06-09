import logging
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from testcontainers.postgres import PostgresContainer

from temdb.models import AcquisitionStatus, AcquisitionTaskStatus
from temdb.server.database import DatabaseManager
from temdb.server.dependencies import get_db_manager
from temdb.server.main import create_app
from temdb.server.sqlmodels import (
    AcquisitionSQLModel,
    AcquisitionTaskSQLModel,
    Base,
    BlockSQLModel,
    CuttingSessionSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SpecimenSQLModel,
    SubstrateSQLModel,
    TileSQLModel,
)

logging.basicConfig(level=logging.INFO)


def _async_database_url(container: PostgresContainer) -> str:
    url = container.get_connection_url()
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as container:
        yield container


@pytest.fixture(scope="function")
async def test_db_manager(postgres_container):
    db_manager = DatabaseManager(database_url=_async_database_url(postgres_container))
    await db_manager.initialize()
    yield db_manager
    if db_manager.sql_engine is not None:
        await db_manager.sql_engine.dispose()


@pytest.fixture(scope="function")
async def init_db(test_db_manager: DatabaseManager):
    if test_db_manager.sql_engine is None:
        raise RuntimeError("SQL engine is not configured for server tests.")
    async with test_db_manager.sql_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture(scope="function")
def app(test_db_manager: DatabaseManager, init_db) -> FastAPI:
    app_instance = create_app()
    app_instance.dependency_overrides[get_db_manager] = lambda: test_db_manager
    yield app_instance
    app_instance.dependency_overrides = {}


@pytest.fixture(scope="function")
async def async_client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(base_url="http://test", transport=ASGITransport(app=app)) as client:
        yield client


@pytest.fixture(scope="function")
async def test_specimen(init_db, test_db_manager: DatabaseManager):
    async with test_db_manager.async_session_factory() as session:
        specimen = SpecimenSQLModel(
            specimen_id="TEST_SPECIMEN_001",
            description="Test specimen for API tests",
            created_at=datetime.now(timezone.utc),
        )
        session.add(specimen)
        await session.commit()
        await session.refresh(specimen)
        yield specimen


@pytest.fixture(scope="function")
async def test_block(init_db, test_db_manager: DatabaseManager, test_specimen: SpecimenSQLModel):
    async with test_db_manager.async_session_factory() as session:
        block = BlockSQLModel(
            block_id="TEST_BLOCK_001",
            specimen_id=test_specimen.specimen_id,
            microCT_info={"resolution": 1.5},
            created_at=datetime.now(timezone.utc),
        )
        session.add(block)
        await session.commit()
        await session.refresh(block)
        yield block


@pytest.fixture(scope="function")
async def test_cutting_session(
    init_db,
    test_db_manager: DatabaseManager,
    test_specimen: SpecimenSQLModel,
    test_block: BlockSQLModel,
):
    async with test_db_manager.async_session_factory() as session:
        cutting_session = CuttingSessionSQLModel(
            cutting_session_id="TEST_CUT_001",
            specimen_id=test_specimen.specimen_id,
            block_id=test_block.block_id,
            start_time=datetime.now(timezone.utc),
            operator="Test Operator",
            sectioning_device="Test Device",
            media_type="tape",
            created_at=datetime.now(timezone.utc),
        )
        session.add(cutting_session)
        await session.commit()
        await session.refresh(cutting_session)
        yield cutting_session


@pytest.fixture(scope="function")
async def test_substrate(init_db, test_db_manager: DatabaseManager):
    async with test_db_manager.async_session_factory() as session:
        substrate = SubstrateSQLModel(
            media_id="SUB001",
            media_type="tape",
            metadata_json={},
            created_at=datetime.now(timezone.utc),
        )
        session.add(substrate)
        await session.commit()
        await session.refresh(substrate)
        yield substrate


@pytest.fixture(scope="function")
async def test_section(
    init_db,
    test_db_manager: DatabaseManager,
    test_cutting_session: CuttingSessionSQLModel,
    test_substrate: SubstrateSQLModel,
):
    async with test_db_manager.async_session_factory() as session:
        section = SectionSQLModel(
            section_id="TEST_SECTION_001",
            section_number=1,
            timestamp=datetime.now(timezone.utc),
            cutting_session_id=test_cutting_session.cutting_session_id,
            block_id=test_cutting_session.block_id,
            specimen_id=test_cutting_session.specimen_id,
            media_id=test_substrate.media_id,
            created_at=datetime.now(timezone.utc),
        )
        session.add(section)
        await session.commit()
        await session.refresh(section)
        yield section


@pytest.fixture(scope="function")
async def test_roi(init_db, test_db_manager: DatabaseManager, test_section: SectionSQLModel):
    async with test_db_manager.async_session_factory() as session:
        roi = ROISQLModel(
            roi_id="SPEC001.BLK001.CS001.SEC001.SUB001.ROI001",
            roi_number=1,
            section_id=test_section.section_id,
            block_id=test_section.block_id,
            specimen_id=test_section.specimen_id,
            substrate_media_id="SUB001",
            hierarchy_level=1,
            parent_roi_id=None,
            updated_at=datetime.now(timezone.utc),
            section_number=test_section.section_number,
            roi_payload={},
            created_at=datetime.now(timezone.utc),
        )
        session.add(roi)
        await session.commit()
        await session.refresh(roi)
        yield roi


@pytest.fixture(scope="function")
async def test_roi2(init_db, test_db_manager: DatabaseManager, test_section: SectionSQLModel):
    async with test_db_manager.async_session_factory() as session:
        roi = ROISQLModel(
            roi_id="SPEC001.BLK001.CS001.SEC001.SUB002.ROI002",
            roi_number=2,
            section_id=test_section.section_id,
            block_id=test_section.block_id,
            specimen_id=test_section.specimen_id,
            substrate_media_id="SUB002",
            hierarchy_level=1,
            parent_roi_id=None,
            updated_at=datetime.now(timezone.utc),
            section_number=test_section.section_number,
            roi_payload={},
            created_at=datetime.now(timezone.utc),
        )
        session.add(roi)
        await session.commit()
        await session.refresh(roi)
        yield roi


@pytest.fixture(scope="function")
async def test_acquisition_task2(
    init_db,
    test_db_manager: DatabaseManager,
    test_specimen: SpecimenSQLModel,
    test_block: BlockSQLModel,
    test_roi2: ROISQLModel,
):
    async with test_db_manager.async_session_factory() as session:
        acquisition_task = AcquisitionTaskSQLModel(
            task_id="TEST_TASK_002",
            specimen_id=test_specimen.specimen_id,
            block_id=test_block.block_id,
            roi_id=test_roi2.roi_id,
            task_type="standard_acquisition",
            version=1,
            status=AcquisitionTaskStatus.PLANNED.value,
            tags=[],
            metadata_json={},
            created_at=datetime.now(timezone.utc),
        )
        session.add(acquisition_task)
        await session.commit()
        await session.refresh(acquisition_task)
        yield acquisition_task


@pytest.fixture(scope="function")
async def test_acquisition_task(
    init_db,
    test_db_manager: DatabaseManager,
    test_specimen: SpecimenSQLModel,
    test_block: BlockSQLModel,
    test_roi: ROISQLModel,
):
    async with test_db_manager.async_session_factory() as session:
        acquisition_task = AcquisitionTaskSQLModel(
            task_id="TEST_TASK_001",
            specimen_id=test_specimen.specimen_id,
            block_id=test_block.block_id,
            roi_id=test_roi.roi_id,
            task_type="standard_acquisition",
            version=1,
            status=AcquisitionTaskStatus.PLANNED.value,
            tags=[],
            metadata_json={},
            created_at=datetime.now(timezone.utc),
        )
        session.add(acquisition_task)
        await session.commit()
        await session.refresh(acquisition_task)
        yield acquisition_task


@pytest.fixture(scope="function")
async def test_acquisition(
    init_db,
    test_db_manager: DatabaseManager,
    test_specimen: SpecimenSQLModel,
    test_roi: ROISQLModel,
    test_acquisition_task: AcquisitionTaskSQLModel,
):
    async with test_db_manager.async_session_factory() as session:
        acquisition = AcquisitionSQLModel(
            acquisition_id="TEST_ACQ_001",
            montage_id="TEST_MONTAGE_001",
            specimen_id=test_specimen.specimen_id,
            roi_id=test_roi.roi_id,
            acquisition_task_id=test_acquisition_task.task_id,
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
            status=AcquisitionStatus.QC_PENDING.value,
            start_time=datetime.now(timezone.utc),
        )
        session.add(acquisition)
        await session.commit()
        await session.refresh(acquisition)
        yield acquisition


@pytest.fixture(scope="function")
async def test_tile(init_db, test_db_manager: DatabaseManager, test_acquisition: AcquisitionSQLModel):
    async with test_db_manager.async_session_factory() as session:
        tile = TileSQLModel(
            tile_id="TEST_TILE_001",
            acquisition_id=test_acquisition.acquisition_id,
            raster_index=1,
            stage_position={"x": 100, "y": 200},
            raster_position={"row": 0, "col": 0},
            focus_score=0.95,
            min_value=0,
            max_value=255,
            mean_value=128,
            std_value=25,
            image_path="/path/to/test/image.tif",
            created_at=datetime.now(timezone.utc),
        )
        session.add(tile)
        await session.commit()
        await session.refresh(tile)
        yield tile
