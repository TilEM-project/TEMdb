import pytest


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


@pytest.mark.asyncio
async def test_full_data_integration(init_db):
    # Generate Specimen
    specimen = generate_specimen()
    await specimen.insert()

    # Generate Block linked to Specimen
    block = generate_block(specimen.id)
    await block.insert()

    # Generate Cutting Session linked to Block
    cutting_session = generate_cutting_session(block.id)
    await cutting_session.insert()

    # Generate Section linked to Cutting Session
    section = generate_section(cutting_session.id)
    await section.insert()

    # Generate ROI linked to Section
    roi = generate_roi(section.id)
    await roi.insert()

    # Generate Imaging Session linked to Specimen and Block
    imaging_session = generate_imaging_session(specimen.id, block.id, roi.id)
    await imaging_session.insert()

    # Generate Acquisition linked to ROI and Imaging Session
    acquisition = generate_acquisition(roi.id, imaging_session.id)
    await acquisition.insert()

    # Generate Tile linked to Acquisition
    tile = generate_tile(acquisition.id)
    await tile.insert()

    # Add Tile to Acquisition
    acquisition.add_tile(tile.id)
    await acquisition.save()

    # Assertions
    assert specimen.id is not None
    assert block.specimen.id == specimen.id
    assert cutting_session.block.id == block.id
    assert section.cut_session.id == cutting_session.id
    assert imaging_session.specimen_id == specimen.id
    assert roi.section.id == section.id
    assert acquisition.roi.id == roi.id
    assert acquisition.imaging_session.id == imaging_session.id
    assert tile.id in acquisition.tile_ids
