async def test_create_acquisition_with_its_roi(transport, records):
    acquisition = await records.acquisition()
    assert acquisition.acquisition_id == "A1"
    assert acquisition.roi_id == (await records.roi()).roi_id
    assert transport.unmatched_requests() == []


async def test_tiles_are_uploaded_gzipped(transport, records):
    tiles = await records.tiles()
    assert len(tiles) == 10
    assert (
        "POST",
        "/api/v2/acquisitions/A1/tiles/bulk",
    ) in transport.gzipped_requests
