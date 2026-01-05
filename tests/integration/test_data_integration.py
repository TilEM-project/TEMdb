import logging

import pytest
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

from tests.integration.generators import (
    generate_acquisition,
    generate_acquisition_task,
    generate_block,
    generate_cutting_session,
    generate_roi,
    generate_section,
    generate_specimen,
    generate_substrate,
    generate_tile,
)

logging.basicConfig(level=logging.INFO)


class TestDataIntegration:
    @pytest.fixture(autouse=True)
    async def setup_test(self, init_db):
        self.db = init_db
        yield

    async def create_specimen(self) -> SpecimenDocument:
        specimen = generate_specimen()
        await specimen.insert()
        return await SpecimenDocument.get(specimen.id)

    async def create_block(self, specimen: SpecimenDocument) -> BlockDocument:
        block = generate_block(specimen)
        await block.insert()
        return await BlockDocument.get(block.id)

    async def create_cutting_session(self, specimen: SpecimenDocument, block: BlockDocument) -> CuttingSessionDocument:
        cutting_session = generate_cutting_session(specimen, block)

        await cutting_session.insert()
        return await CuttingSessionDocument.get(cutting_session.id)

    async def create_substrate(self, cutting_session: CuttingSessionDocument) -> SubstrateDocument:
        create_substrate = generate_substrate(cutting_session)
        await create_substrate.insert()
        return await SubstrateDocument.get(create_substrate.id)

    async def create_section(
        self, cutting_session: CuttingSessionDocument, substrate: SubstrateDocument, section_number: int = 1
    ) -> SectionDocument:
        section = generate_section(cutting_session, substrate, section_number)

        await section.insert()
        return await SectionDocument.get(section.id)

    async def create_roi(self, section: SectionDocument, roi_number: int = 1) -> ROIDocument:
        roi = generate_roi(section, roi_number)

        await roi.insert()
        return await ROIDocument.get(roi.id)

    async def create_acquisition_task(
        self, specimen: SpecimenDocument, block: BlockDocument, roi: ROIDocument
    ) -> AcquisitionTaskDocument:
        task = generate_acquisition_task(specimen, block, roi)

        await task.insert()
        return await AcquisitionTaskDocument.get(task.id)

    async def create_acquisition(
        self, specimen: SpecimenDocument, roi: ROIDocument, task: AcquisitionTaskDocument
    ) -> AcquisitionDocument:
        acq = generate_acquisition(specimen, roi, task)

        await acq.insert()
        return await AcquisitionDocument.get(acq.id)

    async def create_tile(self, acquisition: AcquisitionDocument, raster_index: int) -> TileDocument:
        tile = generate_tile(acquisition, raster_index)

        await tile.insert()
        return await TileDocument.get(tile.id)

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
        assert block.specimen_ref.ref.id == specimen.id
        assert block.specimen_id == specimen.specimen_id

    @pytest.mark.asyncio
    async def test_cutting_session_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)

        assert cutting_session.id is not None
        assert cutting_session.cutting_session_id is not None

        assert cutting_session.block_ref.ref.id == block.id
        assert cutting_session.specimen_ref.ref.id == specimen.id
        assert cutting_session.block_id == block.block_id
        assert cutting_session.specimen_id == specimen.specimen_id

    @pytest.mark.asyncio
    async def test_substrate_creation(self):
        specimen = await self.create_specimen()
        cutting_session = await self.create_cutting_session(specimen, await self.create_block(specimen))
        substrate = await self.create_substrate(cutting_session)

        assert substrate.id is not None
        assert substrate.media_type == "tape"

    @pytest.mark.asyncio
    async def test_section_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate(cutting_session)
        section = await self.create_section(cutting_session, substrate)

        assert section.id is not None
        assert section.section_id is not None
        assert section.cutting_session_ref.ref.id == cutting_session.id
        assert section.cutting_session_id == cutting_session.cutting_session_id
        assert section.block_id == block.block_id
        assert section.specimen_id == specimen.specimen_id

    @pytest.mark.asyncio
    async def test_roi_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate(cutting_session)

        section = await self.create_section(cutting_session, substrate)
        roi = await self.create_roi(section)

        assert roi.id is not None
        assert roi.roi_id is not None
        assert roi.section_ref.ref.id == section.id
        assert roi.section_id == section.section_id
        assert roi.block_id == block.block_id
        assert roi.specimen_id == specimen.specimen_id

    @pytest.mark.asyncio
    async def test_acquisition_task_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate(cutting_session)
        section = await self.create_section(cutting_session, substrate)
        roi = await self.create_roi(section)
        task = await self.create_acquisition_task(specimen, block, roi)

        assert task.id is not None
        assert task.task_id is not None
        assert task.specimen_ref.ref.id == specimen.id
        assert task.block_ref.ref.id == block.id
        assert task.roi_ref.ref.id == roi.id

    @pytest.mark.asyncio
    async def test_acquisition_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate(cutting_session)
        section = await self.create_section(cutting_session, substrate)
        roi = await self.create_roi(section)
        task = await self.create_acquisition_task(specimen, block, roi)
        acquisition = await self.create_acquisition(specimen, roi, task)

        assert acquisition.id is not None
        assert acquisition.acquisition_id is not None
        assert acquisition.specimen_ref.ref.id == specimen.id
        assert acquisition.roi_ref.ref.id == roi.id
        assert acquisition.acquisition_task_ref.ref.id == task.id

        assert acquisition.specimen_id == specimen.specimen_id
        assert acquisition.roi_id == roi.roi_id
        assert acquisition.acquisition_task_id == task.task_id

    @pytest.mark.asyncio
    async def test_single_tile_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate(cutting_session)
        section = await self.create_section(cutting_session, substrate)
        roi = await self.create_roi(section)
        task = await self.create_acquisition_task(specimen, block, roi)
        acquisition = await self.create_acquisition(specimen, roi, task)

        tile = await self.create_tile(acquisition, 1)

        assert tile.id is not None
        assert tile.tile_id is not None
        assert tile.raster_index == 1
        assert tile.acquisition_ref.ref.id == acquisition.id
        assert tile.acquisition_id == acquisition.acquisition_id

        fetched_tile = await TileDocument.find_one(
            TileDocument.acquisition_id == acquisition.acquisition_id, TileDocument.raster_index == 1
        )
        assert fetched_tile is not None
        assert fetched_tile.id == tile.id

    @pytest.mark.asyncio
    async def test_multiple_tiles_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)
        cutting_session = await self.create_cutting_session(specimen, block)
        substrate = await self.create_substrate(cutting_session)
        section = await self.create_section(cutting_session, substrate)
        roi = await self.create_roi(section)
        task = await self.create_acquisition_task(specimen, block, roi)
        acquisition = await self.create_acquisition(specimen, roi, task)

        NUM_TILES = 5
        created_tiles = []
        for i in range(NUM_TILES):
            tile = await self.create_tile(acquisition, i)
            created_tiles.append(tile)

        tiles_count = await TileDocument.find(TileDocument.acquisition_id == acquisition.acquisition_id).count()
        assert tiles_count == NUM_TILES

        fetched_tiles = (
            await TileDocument.find(TileDocument.acquisition_id == acquisition.acquisition_id)
            .sort(+TileDocument.raster_index)
            .to_list()
        )
        assert len(fetched_tiles) == NUM_TILES
        for i in range(NUM_TILES):
            assert fetched_tiles[i].id == created_tiles[i].id
            assert fetched_tiles[i].raster_index == i
            assert fetched_tiles[i].acquisition_id == acquisition.acquisition_id
