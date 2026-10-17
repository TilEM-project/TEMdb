from tests.integration.client.live import unmatched_requests


def test_requests_to_existing_routes_are_matched(live_app):
    assert unmatched_requests(live_app, [("GET", "/api/v2/specimens"), ("GET", "/api/v2/specimens/SP1")]) == []


def test_request_to_missing_path_is_reported(live_app):
    missing = ("GET", "/api/v2/acquisitions/A1/complete-metadata")
    assert unmatched_requests(live_app, [missing]) == [missing]


def test_request_with_wrong_method_is_reported(live_app):
    assert unmatched_requests(live_app, [("PUT", "/api/v2/specimens")]) == [("PUT", "/api/v2/specimens")]


async def test_seed_builds_the_acquisition_chain_through_the_client(live, seed):
    acquisition = await seed.acquisition()
    assert acquisition.acquisition_id == "A1"
    assert acquisition.roi_id == (await seed.roi()).roi_id
    assert live.unmatched_requests() == []


async def test_seed_tiles_upload_a_gzipped_body(live, seed):
    tiles = await seed.tiles()
    assert len(tiles) == 10
    assert (
        "POST",
        "/api/v2/acquisitions/A1/tiles/bulk",
    ) in live.transport.gzipped_requests
