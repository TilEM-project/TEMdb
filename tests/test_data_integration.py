import pytest
import logging
from tests.generators import (
    generate_specimen,
    generate_block,
    generate_cutting_session,
    generate_substrate,
    generate_section,
    generate_acquisition_task,
    generate_roi,
    generate_acquisition,
    generate_tile,
)
from temdb.models.v2.specimen import Specimen
from temdb.models.v2.block import Block
from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.substrate import Substrate
from temdb.models.v2.section import Section
from temdb.models.v2.roi import ROI
from temdb.models.v2.task import AcquisitionTask
from temdb.models.v2.acquisition import Acquisition
from temdb.models.v2.tile import Tile

logging.basicConfig(level=logging.INFO)
from bson import DBRef # Import DBRef

class TestDataIntegration:
    @pytest.fixture(autouse=True)
    async def setup_test(self, init_db):
        """Ensure database is initialized for each test method."""
        self.db = init_db
        yield

    async def create_specimen(self) -> Specimen:
        """Helper to create and insert a specimen using generator."""
        specimen = generate_specimen()
        await specimen.insert()
        return await Specimen.get(specimen.id)

    async def create_block(self, specimen: Specimen) -> Block:
        """Helper to create and insert a block linked to a specimen."""
        block = generate_block(specimen) 
        await block.insert()
        return await Block.get(block.id)

    async def create_cutting_session(self, specimen: Specimen, block: Block) -> CuttingSession:
        """Helper to create and insert a cutting session."""
        cutting_session = generate_cutting_session(specimen, block)
 
        await cutting_session.insert()
        return await CuttingSession.get(cutting_session.id)
    
    async def create_substrate(self, cutting_session: CuttingSession) -> Substrate:
        create_substrate = generate_substrate(cutting_session)
        await create_substrate.insert()
        return await Substrate.get(create_substrate.id)

    async def create_section(self, cutting_session: CuttingSession, substrate: Substrate, section_number: int = 1) -> Section:
         """Helper to create and insert a section."""
         section = generate_section(cutting_session, substrate, section_number)
 
         await section.insert()
         return await Section.get(section.id)

    async def create_roi(self, section: Section, roi_id: int = 1) -> ROI:
        """Helper to create and insert an ROI."""
        roi = generate_roi(section, roi_id) 

        await roi.insert()
        return await ROI.get(roi.id)

    async def create_acquisition_task(self, specimen: Specimen, block: Block, roi: ROI) -> AcquisitionTask:
        """Helper to create and insert a task."""
        task = generate_acquisition_task(specimen, block, roi)

        await task.insert()
        return await AcquisitionTask.get(task.id)

    async def create_acquisition(self, specimen: Specimen, roi: ROI, task: AcquisitionTask) -> Acquisition:
        """Helper to create and insert an acquisition."""
        acq = generate_acquisition(specimen, roi, task) 

        await acq.insert()
        return await Acquisition.get(acq.id)

    async def create_tile(self, acquisition: Acquisition, raster_index: int) -> Tile:
        """Helper to create and insert a tile."""
        tile = generate_tile(acquisition, raster_index) 

        await tile.insert()
        return await Tile.get(tile.id)


    @pytest.mark.asyncio
    async def test_specimen_creation(self):
        """Test basic specimen creation."""
        specimen = await self.create_specimen()
        assert specimen.id is not None
        assert specimen.specimen_id is not None 

    @pytest.mark.asyncio
    async def test_block_creation(self):
        """Test block creation and linking to specimen."""
        specimen = await self.create_specimen()
        block = await self.create_block(specimen)

        assert block.id is not None
        assert block.block_id is not None 
        assert block.specimen_ref.ref.id == specimen.id
        assert block.specimen_id == specimen.specimen_id

    @pytest.mark.asyncio
    async def test_cutting_session_creation(self):
        """Test cutting session creation and linking."""
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
        """Test substrate creation and linking."""
        specimen = await self.create_specimen()
        cutting_session = await self.create_cutting_session(specimen, await self.create_block(specimen))
        substrate = await self.create_substrate(cutting_session)

        assert substrate.id is not None
        assert substrate.media_type == "tape"

    @pytest.mark.asyncio
    async def test_section_creation(self):
        """Test section creation and linking."""
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
        """Test ROI creation and linking."""
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
        assert roi.cutting_session_id == cutting_session.cutting_session_id
        assert roi.block_id == block.block_id
        assert roi.specimen_id == specimen.specimen_id

    @pytest.mark.asyncio
    async def test_acquisition_task_creation(self):
        """Test AcquisitionTask creation and linking."""
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
        """Test Acquisition creation and linking."""
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
        """Test single tile creation and linking."""
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

        fetched_tile = await Tile.find_one(Tile.acquisition_id == acquisition.acquisition_id, Tile.raster_index == 1)
        assert fetched_tile is not None
        assert fetched_tile.id == tile.id

    @pytest.mark.asyncio
    async def test_multiple_tiles_creation(self):
        """Test creation of multiple tiles for one acquisition."""
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

        tiles_count = await Tile.find(Tile.acquisition_id == acquisition.acquisition_id).count()
        assert tiles_count == NUM_TILES

        fetched_tiles = await Tile.find(Tile.acquisition_id == acquisition.acquisition_id).sort(+Tile.raster_index).to_list()
        assert len(fetched_tiles) == NUM_TILES
        for i in range(NUM_TILES):
            assert fetched_tiles[i].id == created_tiles[i].id
            assert fetched_tiles[i].raster_index == i
            assert fetched_tiles[i].acquisition_id == acquisition.acquisition_id