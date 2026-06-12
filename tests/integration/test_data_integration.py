from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from temdb.models import AcquisitionTaskStatus
from temdb.server.database import DatabaseManager
from temdb.server.ids import uuid7
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


class TestDataIntegration:
    @pytest.fixture(autouse=True)
    async def setup_test(self, init_db: DatabaseManager):
        self.db_manager = init_db
        yield

    async def create_specimen(self) -> SpecimenSQLModel:
        async with self.db_manager.async_session_factory() as session:
            specimen = SpecimenSQLModel(
                specimen_id=f"SPEC_{int(datetime.now(timezone.utc).timestamp())}",
                description="integration specimen",
                created_at=datetime.now(timezone.utc),
            )
            session.add(specimen)
            await session.commit()
            await session.refresh(specimen)
            return specimen

    async def create_block(self, specimen: SpecimenSQLModel) -> BlockSQLModel:
        async with self.db_manager.async_session_factory() as session:
            block = BlockSQLModel(
                block_id=f"BLOCK_{specimen.specimen_id}",
                specimen_id=specimen.specimen_id,
                microCT_info={"resolution": 1.5},
                created_at=datetime.now(timezone.utc),
            )
            session.add(block)
            await session.commit()
            await session.refresh(block)
            return block

    async def create_cutting_session(
        self,
        specimen: SpecimenSQLModel,
        block: BlockSQLModel,
    ) -> CuttingSessionSQLModel:
        async with self.db_manager.async_session_factory() as session:
            cutting_session = CuttingSessionSQLModel(
                cutting_session_id=f"CUT_{block.block_id}",
                specimen_id=specimen.specimen_id,
                block_id=block.block_id,
                start_time=datetime.now(timezone.utc),
                operator="integration operator",
                sectioning_device="integration device",
                media_type="tape",
                created_at=datetime.now(timezone.utc),
            )
            session.add(cutting_session)
            await session.commit()
            await session.refresh(cutting_session)
            return cutting_session

    async def create_substrate(self) -> SubstrateSQLModel:
        async with self.db_manager.async_session_factory() as session:
            substrate = SubstrateSQLModel(
                media_id=f"SUB_{int(datetime.now(timezone.utc).timestamp())}",
                media_type="tape",
                metadata_json={},
                created_at=datetime.now(timezone.utc),
            )
            session.add(substrate)
            await session.commit()
            await session.refresh(substrate)
            return substrate

    async def create_section(
        self,
        cutting_session: CuttingSessionSQLModel,
        substrate: SubstrateSQLModel,
        section_number: int = 1,
    ) -> SectionSQLModel:
        async with self.db_manager.async_session_factory() as session:
            section = SectionSQLModel(
                section_id=f"SEC_{cutting_session.cutting_session_id}_{section_number:03d}",
                section_number=section_number,
                timestamp=datetime.now(timezone.utc),
                cutting_session_id=cutting_session.cutting_session_id,
                block_id=cutting_session.block_id,
                specimen_id=cutting_session.specimen_id,
                media_id=substrate.media_id,
                created_at=datetime.now(timezone.utc),
            )
            session.add(section)
            await session.commit()
            await session.refresh(section)
            return section

    async def create_roi(self, section: SectionSQLModel, roi_number: int = 1) -> ROISQLModel:
        async with self.db_manager.async_session_factory() as session:
            roi = ROISQLModel(
                roi_id=f"{section.specimen_id}.{section.block_id}.{section.section_id}.{section.media_id}.ROI{roi_number:03d}",
                roi_number=roi_number,
                section_id=section.section_id,
                block_id=section.block_id,
                specimen_id=section.specimen_id,
                substrate_media_id=section.media_id,
                hierarchy_level=1,
                section_number=section.section_number,
                roi_payload={},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(roi)
            await session.commit()
            await session.refresh(roi)
            return roi

    async def create_acquisition_task(
        self,
        specimen: SpecimenSQLModel,
        block: BlockSQLModel,
        roi: ROISQLModel,
    ) -> AcquisitionTaskSQLModel:
        async with self.db_manager.async_session_factory() as session:
            task = AcquisitionTaskSQLModel(
                task_id=f"TASK_{roi.roi_id}",
                specimen_id=specimen.specimen_id,
                block_id=block.block_id,
                roi_id=roi.roi_id,
                task_type="standard_acquisition",
                version=1,
                status=AcquisitionTaskStatus.PLANNED.value,
                tags=[],
                metadata_json={},
                created_at=datetime.now(timezone.utc),
            )
            session.add(task)
            await session.commit()
            await session.refresh(task)
            return task

    async def create_acquisition(
        self,
        specimen: SpecimenSQLModel,
        roi: ROISQLModel,
        task: AcquisitionTaskSQLModel,
    ) -> AcquisitionSQLModel:
        async with self.db_manager.async_session_factory() as session:
            dataset = DatasetSQLModel(
                dataset_id=uuid7(),
                name=f"DS_{task.task_id}",
                specimen_id=specimen.specimen_id,
                size_class="small",
                created_at=datetime.now(timezone.utc),
            )
            session.add(dataset)
            microscope = MicroscopeSQLModel(label=f"SCOPE_{task.task_id}")
            session.add(microscope)
            await session.commit()
            await session.refresh(dataset)
            await session.refresh(microscope)
            acq = AcquisitionSQLModel(
                acquisition_id=f"ACQ_{task.task_id}",
                montage_id=f"MONT_{task.task_id}",
                specimen_id=specimen.specimen_id,
                roi_id=roi.roi_id,
                acquisition_task_id=task.task_id,
                dataset_id=dataset.dataset_id,
                hardware_settings={
                    "scope_id": "SEM_1",
                    "camera_model": "CamA",
                    "camera_serial": "SERIAL",
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
                microscope_id=microscope.microscope_id,
                tilt_angle_deg=0.0,
                start_time=datetime.now(timezone.utc),
            )
            session.add(acq)
            await session.commit()
            await session.refresh(acq)
            return acq

    async def create_tile(self, acquisition: AcquisitionSQLModel, raster_index: int) -> TileSQLModel:
        async with self.db_manager.async_session_factory() as session:
            await ensure_tile_partition(session, acquisition.dataset_id)
            tile = TileSQLModel(
                tile_id=uuid7(),
                dataset_id=acquisition.dataset_id,
                acquisition_id=acquisition.acquisition_id,
                raster_index=raster_index,
                stage_x_nm=float(raster_index),
                stage_y_nm=float(raster_index),
                montage_row=raster_index // 10,
                montage_col=raster_index % 10,
                focus_score=0.9,
                min_value=0.0,
                max_value=65535.0,
                mean_value=10000.0,
                std_value=500.0,
                image_path=f"/tmp/{raster_index}.tif",
                created_at=datetime.now(timezone.utc),
            )
            session.add(tile)
            await session.commit()
            await session.refresh(tile)
            return tile

    @pytest.mark.asyncio
    async def test_specimen_creation(self):
        specimen = await self.create_specimen()
        assert specimen.id is not None
        assert specimen.specimen_id is not None

    @pytest.mark.asyncio
    async def test_block_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        assert block.id is not None
        assert block.block_id is not None
        assert block.specimen_id == specimen.specimen_id

    @pytest.mark.asyncio
    async def test_cutting_session_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        assert cutting_session.id is not None
        assert cutting_session.cutting_session_id is not None
        assert cutting_session.block_id == block.block_id
        assert cutting_session.specimen_id == specimen.specimen_id

    @pytest.mark.asyncio
    async def test_substrate_creation(self):
        substrate = await self.create_substrate()
        assert substrate.id is not None
        assert substrate.media_type == "tape"

    @pytest.mark.asyncio
    async def test_section_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate()
        section = await self.create_section(cutting_session, substrate)
        assert section.id is not None
        assert section.section_id is not None
        assert section.cutting_session_id == cutting_session.cutting_session_id
        assert section.block_id == block.block_id
        assert section.specimen_id == specimen.specimen_id

    @pytest.mark.asyncio
    async def test_roi_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate()
        section = await self.create_section(cutting_session, substrate)
        roi = await self.create_roi(section)
        assert roi.id is not None
        assert roi.roi_id is not None
        assert roi.section_id == section.section_id
        assert roi.block_id == block.block_id
        assert roi.specimen_id == specimen.specimen_id

    @pytest.mark.asyncio
    async def test_acquisition_task_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate()
        section = await self.create_section(cutting_session, substrate)
        roi = await self.create_roi(section)
        task = await self.create_acquisition_task(specimen, block, roi)
        assert task.id is not None
        assert task.task_id is not None
        assert task.specimen_id == specimen.specimen_id
        assert task.block_id == block.block_id
        assert task.roi_id == roi.roi_id

    @pytest.mark.asyncio
    async def test_acquisition_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate()
        section = await self.create_section(cutting_session, substrate)
        roi = await self.create_roi(section)
        task = await self.create_acquisition_task(specimen, block, roi)
        acquisition = await self.create_acquisition(specimen, roi, task)
        assert acquisition.id is not None
        assert acquisition.acquisition_id is not None
        assert acquisition.specimen_id == specimen.specimen_id
        assert acquisition.roi_id == roi.roi_id
        assert acquisition.acquisition_task_id == task.task_id

    @pytest.mark.asyncio
    async def test_single_tile_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate()
        section = await self.create_section(cutting_session, substrate)
        roi = await self.create_roi(section)
        task = await self.create_acquisition_task(specimen, block, roi)
        acquisition = await self.create_acquisition(specimen, roi, task)
        tile = await self.create_tile(acquisition, 1)
        assert tile.tile_id is not None
        assert tile.raster_index == 1
        assert tile.acquisition_id == acquisition.acquisition_id

        async with self.db_manager.async_session_factory() as session:
            fetched_tile = (
                await session.exec(
                    select(TileSQLModel).where(
                        TileSQLModel.acquisition_id == acquisition.acquisition_id,
                        TileSQLModel.raster_index == 1,
                    )
                )
            ).first()
        assert fetched_tile is not None
        assert fetched_tile.tile_id == tile.tile_id

    @pytest.mark.asyncio
    async def test_multiple_tiles_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate()
        section = await self.create_section(cutting_session, substrate)
        roi = await self.create_roi(section)
        task = await self.create_acquisition_task(specimen, block, roi)
        acquisition = await self.create_acquisition(specimen, roi, task)

        num_tiles = 5
        created_tiles = []
        for i in range(num_tiles):
            tile = await self.create_tile(acquisition, i)
            created_tiles.append(tile)

        async with self.db_manager.async_session_factory() as session:
            fetched_tiles = (
                await session.exec(
                    select(TileSQLModel)
                    .where(TileSQLModel.acquisition_id == acquisition.acquisition_id)
                    .order_by(TileSQLModel.raster_index)
                )
            ).all()
        assert len(fetched_tiles) == num_tiles
        for i in range(num_tiles):
            assert fetched_tiles[i].tile_id == created_tiles[i].tile_id
            assert fetched_tiles[i].raster_index == i
            assert fetched_tiles[i].acquisition_id == acquisition.acquisition_id
