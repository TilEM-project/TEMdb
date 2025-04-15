import pytest
import logging
from tests.generators import (
    generate_specimen,
    generate_block,
    generate_cutting_session,
    generate_section,
    generate_imaging_tasks,
    generate_roi,
    generate_acquisition,
    generate_tile,
)
from temdb.models.v2.tile import Tile

logging.basicConfig(level=logging.INFO)


class TestDataIntegration:
    @pytest.fixture(autouse=True)
    async def setup_test(self, init_db):
        self.db = init_db
        yield

    async def create_specimen(self):
        specimen = generate_specimen()
        await specimen.insert()
        return specimen

    async def create_block(self, specimen_id):
        block = generate_block(specimen_id)
        await block.insert()
        return block

    @pytest.mark.asyncio
    async def test_specimen_creation(self):
        specimen = await self.create_specimen()
        assert specimen.id is not None

    @pytest.mark.asyncio
    async def test_block_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen.id)

        assert block.id is not None
        assert block.specimen_id.ref.id == specimen.id

    @pytest.mark.asyncio
    async def test_cutting_session_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen.id)

        cutting_session = generate_cutting_session(specimen.id, block.id)
        await cutting_session.insert()

        assert cutting_session.id is not None
        assert cutting_session.block_id.ref.id == block.id

    @pytest.mark.asyncio
    async def test_section_creation(self):
        specimen = await self.create_specimen()
        block = await self.create_block(specimen.id)
        cutting_session = generate_cutting_session(specimen.id, block.id)
        await cutting_session.insert()

        section = generate_section(cutting_session.id)
        await section.insert()

        assert section.id is not None
        assert section.cutting_session_id.ref.id == cutting_session.id

    @pytest.mark.asyncio
    async def test_single_tile_creation(self):
        # Setup
        specimen = await self.create_specimen()
        block = await self.create_block(specimen.id)
        cutting_session = generate_cutting_session(specimen.id, block.id)
        await cutting_session.insert()
        section = generate_section(cutting_session.id)
        await section.insert()

        # Create ROI with proper linking
        roi = generate_roi(section.section_number)
        await roi.insert()

        # Create imaging session with roi.id instead of the ROI object
        acquisition_task = generate_imaging_tasks(specimen.id, block.id, [roi.id])
        await acquisition_task.insert()

        # Create acquisition
        acquisition = generate_acquisition(specimen.id, roi.id, acquisition_task.id)
        await acquisition.insert()

        # Create and test tile
        tile = generate_tile(1, acquisition.id)
        await tile.insert()

        # Verify tile creation
        fetched_tile = await Tile.find_one(Tile.acquisition_id.id == acquisition.id)
        assert fetched_tile is not None
        assert fetched_tile.acquisition_id.ref.id == acquisition.id

    @pytest.mark.asyncio
    async def test_multiple_tiles_creation(self):
        # Setup
        specimen = await self.create_specimen()
        block = await self.create_block(specimen.id)
        cutting_session = generate_cutting_session(specimen.id, block.id)
        await cutting_session.insert()
        section = generate_section(cutting_session.id)
        await section.insert()

        # Create ROI with proper linking
        roi = generate_roi(section.section_number)
        await roi.insert()

        # Create imaging session with roi.id
        acquisition_task = generate_imaging_tasks(specimen.id, block.id, [roi.id])
        await acquisition_task.insert()

        # Create acquisition
        acquisition = generate_acquisition(specimen.id, roi.id, acquisition_task.id)
        await acquisition.insert()

        # Create multiple tiles
        NUM_TILES = 10
        for tile_id in range(NUM_TILES):
            tile = generate_tile(tile_id, acquisition.id)
            await tile.insert()

        # Query using the proper reference to acquisition.id
        tiles_count = await Tile.find(Tile.acquisition_id.id == acquisition.id).count()
        assert tiles_count == NUM_TILES
