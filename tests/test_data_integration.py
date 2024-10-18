import pytest
import logging

from tests.generators import (
    generate_specimen,
    generate_block,
    generate_cutting_session,
    generate_section,
    generate_imaging_session,
    generate_roi,
    generate_acquisition,
    generate_tile,
)

from temdb.models.v2.tile import Tile

logging.basicConfig(level=logging.INFO)



@pytest.mark.asyncio
async def test_full_data_integration(init_db):
    # Generate Specimen
    
    specimen = generate_specimen()
    await specimen.insert()
    
    # Generate Block linked to Specimen
    block = generate_block(specimen.id)
    await block.insert()

    # Generate Cutting Session linked to Block
    cutting_session = generate_cutting_session(specimen.id, block.id)
    await cutting_session.insert()

    # Generate Section linked to Cutting Session
    section = generate_section(cutting_session.id)
    await section.insert()

    # Generate ROI linked to Section
    roi = generate_roi(section.section_number)
    await roi.insert()

    # Generate Imaging Session linked to Specimen and Block
    imaging_session = generate_imaging_session(specimen.id, block.id, roi)
    await imaging_session.insert()
    logging.info(imaging_session)
    # Generate Acquisition linked to ROI and Imaging Session
    acquisition = generate_acquisition(specimen.id, roi.id, imaging_session.id)
    await acquisition.insert()

    # add many tiles 
    for tile_id in range(10):
        tile = generate_tile(tile_id, acquisition.acquisition_id)
        await tile.insert()

    # get tiles
    tiles = Tile.find_many(Tile.acquisition_id == acquisition.acquisition_id).count()
    logging.info(tiles)
    # assert await tiles.to_list() == 10
    # Assertions
    assert specimen.id is not None
    assert block.id is not None
    assert cutting_session.id is not None
    assert section.id is not None
    assert roi.id is not None
    assert imaging_session.id is not None
    assert acquisition.id is not None

    
    # Check if all tiles are inserted
    # tiles = await Tile.find({"acquisition_id": acquisition.id}).to_list()
    # assert len(tiles) == 500
