import itertools
import logging
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from temdb.server.database import DatabaseManager
from temdb.server.dependencies import get_db_manager
from temdb.server.ids import uuid7
from temdb.server.main import create_app
from temdb.server.sqlmodels import (
    AcquisitionSQLModel,
    AcquisitionTaskSQLModel,
    BlockSQLModel,
    CuttingSessionSQLModel,
    DatasetSQLModel,
    MicroscopeSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SpecimenSQLModel,
    SubstrateSQLModel,
    TileSQLModel,
)
from temdb.server.sqlmodels.tile_partition import ensure_tile_partition
from tests.conftest import async_database_url

logging.basicConfig(level=logging.INFO)


_fresh_db_counter = itertools.count()


@pytest.fixture(scope="function")
async def fresh_database_url(postgres_container):
    admin_url = async_database_url(postgres_container)
    db_name = f"temdb_fresh_{next(_fresh_db_counter)}"
    engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    await engine.dispose()
    yield admin_url.rsplit("/", 1)[0] + f"/{db_name}"


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="function")
async def async_client(
    app: FastAPI, test_db_manager: DatabaseManager, init_db
) -> AsyncClient:
    app.dependency_overrides[get_db_manager] = lambda: test_db_manager
    try:
        async with AsyncClient(
            base_url="http://test", transport=ASGITransport(app=app)
        ) as client:
            yield client
    finally:
        app.dependency_overrides = {}


async def _seed(db_manager: DatabaseManager, row):
    async with db_manager.async_session_factory() as session:
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row


@pytest.fixture(scope="function")
async def test_specimen(init_db, test_db_manager: DatabaseManager):
    return await _seed(
        test_db_manager,
        SpecimenSQLModel(
            specimen_id="TEST_SPECIMEN_001",
            description="Test specimen for API tests",
            created_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_dataset(
    init_db, test_db_manager: DatabaseManager, test_specimen: SpecimenSQLModel
):
    return await _seed(
        test_db_manager,
        DatasetSQLModel(
            dataset_id=uuid7(),
            name="TEST_DATASET_001",
            specimen_id=test_specimen.specimen_id,
            size_class="small",
            created_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_block(
    init_db, test_db_manager: DatabaseManager, test_specimen: SpecimenSQLModel
):
    return await _seed(
        test_db_manager,
        BlockSQLModel(
            block_id="TEST_BLOCK_001",
            specimen_id=test_specimen.specimen_id,
            microCT_info={"resolution": 1.5},
            created_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_cutting_session(
    init_db,
    test_db_manager: DatabaseManager,
    test_specimen: SpecimenSQLModel,
    test_block: BlockSQLModel,
):
    return await _seed(
        test_db_manager,
        CuttingSessionSQLModel(
            cutting_session_id="TEST_CUT_001",
            specimen_id=test_specimen.specimen_id,
            block_id=test_block.block_id,
            start_time=datetime.now(timezone.utc),
            operator="Test Operator",
            sectioning_device="Test Device",
            media_type="tape",
            created_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_substrate(init_db, test_db_manager: DatabaseManager):
    return await _seed(
        test_db_manager,
        SubstrateSQLModel(
            media_id="SUB001",
            media_type="tape",
            metadata_json={},
            created_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_section(
    init_db,
    test_db_manager: DatabaseManager,
    test_cutting_session: CuttingSessionSQLModel,
    test_substrate: SubstrateSQLModel,
):
    return await _seed(
        test_db_manager,
        SectionSQLModel(
            section_id="TEST_SECTION_001",
            section_number=1,
            timestamp=datetime.now(timezone.utc),
            cutting_session_id=test_cutting_session.cutting_session_id,
            block_id=test_cutting_session.block_id,
            specimen_id=test_cutting_session.specimen_id,
            media_id=test_substrate.media_id,
            created_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_roi(
    init_db,
    test_db_manager: DatabaseManager,
    test_section: SectionSQLModel,
    test_dataset: DatasetSQLModel,
):
    return await _seed(
        test_db_manager,
        ROISQLModel(
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
            dataset_id=test_dataset.dataset_id,
            created_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_roi2(
    init_db, test_db_manager: DatabaseManager, test_section: SectionSQLModel
):
    return await _seed(
        test_db_manager,
        ROISQLModel(
            roi_id="SPEC001.BLK001.CS001.SEC001.SUB001.ROI002",
            roi_number=2,
            section_id=test_section.section_id,
            block_id=test_section.block_id,
            specimen_id=test_section.specimen_id,
            substrate_media_id=test_section.media_id,
            hierarchy_level=1,
            parent_roi_id=None,
            updated_at=datetime.now(timezone.utc),
            section_number=test_section.section_number,
            roi_payload={},
            created_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_acquisition_task2(
    init_db,
    test_db_manager: DatabaseManager,
    test_specimen: SpecimenSQLModel,
    test_block: BlockSQLModel,
    test_roi2: ROISQLModel,
):
    return await _seed(
        test_db_manager,
        AcquisitionTaskSQLModel(
            task_id="TEST_TASK_002",
            specimen_id=test_specimen.specimen_id,
            block_id=test_block.block_id,
            roi_id=test_roi2.roi_id,
            kind="montage",
            tags=[],
            metadata_json={},
            created_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_acquisition_task(
    init_db,
    test_db_manager: DatabaseManager,
    test_specimen: SpecimenSQLModel,
    test_block: BlockSQLModel,
    test_roi: ROISQLModel,
    test_dataset: DatasetSQLModel,
):
    return await _seed(
        test_db_manager,
        AcquisitionTaskSQLModel(
            task_id="TEST_TASK_001",
            specimen_id=test_specimen.specimen_id,
            block_id=test_block.block_id,
            roi_id=test_roi.roi_id,
            kind="montage",
            tags=[],
            metadata_json={},
            dataset_id=test_dataset.dataset_id,
            created_at=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_microscope(init_db, test_db_manager: DatabaseManager):
    return await _seed(test_db_manager, MicroscopeSQLModel(label="TEST_SCOPE_001"))


@pytest.fixture(scope="function")
async def test_acquisition(
    init_db,
    test_db_manager: DatabaseManager,
    test_specimen: SpecimenSQLModel,
    test_roi: ROISQLModel,
    test_acquisition_task: AcquisitionTaskSQLModel,
    test_dataset: DatasetSQLModel,
    test_microscope: MicroscopeSQLModel,
):
    return await _seed(
        test_db_manager,
        AcquisitionSQLModel(
            acquisition_id="TEST_ACQ_001",
            montage_id="TEST_MONTAGE_001",
            specimen_id=test_specimen.specimen_id,
            roi_id=test_roi.roi_id,
            acquisition_task_id=test_acquisition_task.task_id,
            dataset_id=test_dataset.dataset_id,
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
            microscope_id=test_microscope.microscope_id,
            start_time=datetime.now(timezone.utc),
        ),
    )


@pytest.fixture(scope="function")
async def test_tile(
    init_db,
    test_db_manager: DatabaseManager,
    test_dataset: DatasetSQLModel,
    test_acquisition: AcquisitionSQLModel,
):
    async with test_db_manager.async_session_factory() as session:
        await ensure_tile_partition(session, test_dataset.dataset_id)
        await session.commit()
    return await _seed(
        test_db_manager,
        TileSQLModel(
            tile_id=uuid7(),
            dataset_id=test_dataset.dataset_id,
            run_id=test_acquisition.run_id,
            raster_index=1,
            stage_x_nm=100.0,
            stage_y_nm=200.0,
            montage_row=0,
            montage_col=0,
            focus_score=0.95,
            min_value=0,
            max_value=255,
            mean_value=128,
            std_value=25,
            image_path="/path/to/test/image.tif",
            created_at=datetime.now(timezone.utc),
        ),
    )
