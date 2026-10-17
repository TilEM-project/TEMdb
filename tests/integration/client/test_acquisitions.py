import uuid

import pytest

from temdb.client.exceptions import TEMdbNotFoundError
from temdb.models import (
    AcquisitionUpdate,
    StorageLocationCreate,
    TileUpdate,
)
from tests.integration.client.live import acquisition_payload, tile_payload


async def test_acquisition_create(live, seed):
    client = live.client
    roi = await seed.roi()
    await seed.task()
    microscope = await seed.microscope()
    dataset = await seed.dataset()
    await client.acquisition.create(
        acquisition_payload("A-NEW", roi.roi_id, microscope.microscope_id, dataset.dataset_id)
    )
    assert (await client.acquisition.get("A-NEW")).roi_id == roi.roi_id


async def test_acquisition_get(live, seed):
    client = live.client
    await seed.acquisition()
    assert (await client.acquisition.get("A1")).acquisition_task_id == "T1"


async def test_acquisition_list(live, seed):
    client = live.client
    roi = await seed.roi()
    await seed.acquisition()
    microscope = await seed.microscope()
    dataset = await seed.dataset()
    await client.acquisition.create(acquisition_payload("A2", roi.roi_id, microscope.microscope_id, dataset.dataset_id))
    page = await client.acquisition.list()
    assert {a.acquisition_id for a in page.acquisitions} == {"A1", "A2"}
    page = await client.acquisition.list(limit=1)
    assert len(page.acquisitions) == 1
    await client.acquisition.update("A2", AcquisitionUpdate(montage_set_name="set-2"))
    page = await client.acquisition.list(montage_set_name="set-2")
    assert [a.acquisition_id for a in page.acquisitions] == ["A2"]


async def test_acquisition_list_with_full_metadata(live, seed):
    client = live.client
    await seed.acquisition()
    result = await client.acquisition.list_with_full_metadata()
    assert [row["acquisition"]["acquisition_id"] for row in result["acquisitions"]] == ["A1"]


async def test_acquisition_get_with_full_metadata(live, seed):
    client = live.client
    acquisition = await seed.acquisition()
    full = await client.acquisition.get_with_full_metadata("A1")
    assert full.acquisition.acquisition_id == "A1"
    assert full.roi["roi_id"] == acquisition.roi_id


async def test_acquisition_get_complete_metadata(live, seed):
    client = live.client
    await seed.acquisition()
    assert (await client.acquisition.get_complete_metadata("A1"))["acquisition"]["acquisition_id"] == "A1"


async def test_acquisition_update(live, seed):
    client = live.client
    await seed.acquisition()
    updated = await client.acquisition.update("A1", AcquisitionUpdate(montage_set_name="set-1"))
    assert updated.montage_set_name == "set-1"


async def test_acquisition_delete(live, seed):
    client = live.client
    await seed.acquisition()
    await client.acquisition.delete("A1")
    with pytest.raises(TEMdbNotFoundError):
        await client.acquisition.get("A1")


async def test_acquisition_add_storage_location(live, seed):
    client = live.client
    await seed.acquisition()
    updated = await client.acquisition.add_storage_location(
        "A1", StorageLocationCreate(location_type="local", base_path="/data/A1")
    )
    assert [loc.base_path for loc in updated.storage_locations] == ["/data/A1"]


async def test_acquisition_get_current_storage_location(live, seed):
    client = live.client
    await seed.acquisition()
    for path in ("/data/old", "/data/new"):
        await client.acquisition.add_storage_location(
            "A1", StorageLocationCreate(location_type="local", base_path=path)
        )
    assert (await client.acquisition.get_current_storage_location("A1")).base_path == "/data/new"


async def test_acquisition_get_minimap_uri(live, seed):
    client = live.client
    await seed.acquisition()
    await client.acquisition.add_storage_location(
        "A1", StorageLocationCreate(location_type="local", base_path="/data/A1")
    )
    assert await client.acquisition.get_minimap_uri("A1") == {"minimap_uri": "/data/A1/minimap.png"}


async def test_acquisition_add_tile(live, seed):
    client = live.client
    await seed.acquisition()
    tile = await client.acquisition.add_tile("A1", tile_payload(0))
    assert (await client.acquisition.get_tile("A1", tile.tile_id)).raster_index == 0


async def test_acquisition_add_tiles_bulk(live, seed):
    client = live.client
    await seed.acquisition()
    first = await client.acquisition.add_tiles_bulk("A1", [tile_payload(i) for i in range(10)])
    again = await client.acquisition.add_tiles_bulk("A1", [tile_payload(i) for i in range(10)])
    assert first["inserted"] == 10
    assert again["inserted"] == 0
    assert again["skipped_existing"] == 10


async def test_acquisition_get_tile(live, seed):
    client = live.client
    tiles = await seed.tiles()
    fetched = await client.acquisition.get_tile("A1", tiles[3].tile_id)
    assert fetched.raster_index == tiles[3].raster_index


async def test_acquisition_get_tiles(live, seed):
    client = live.client
    await seed.tiles()
    first = await client.acquisition.get_tiles("A1", limit=4)
    second = await client.acquisition.get_tiles("A1", cursor=first.metadata["next_cursor"], limit=4)
    assert [t.raster_index for t in first.tiles] == [0, 1, 2, 3]
    assert [t.raster_index for t in second.tiles] == [4, 5, 6, 7]


async def test_acquisition_get_all_tiles(live, seed):
    client = live.client
    await seed.tiles()
    tiles = await client.acquisition.get_all_tiles("A1", page_limit=3)
    assert [t.raster_index for t in tiles] == list(range(10))


async def test_acquisition_get_tile_count(live, seed):
    client = live.client
    await seed.tiles()
    assert await client.acquisition.get_tile_count("A1") == {"tile_count": 10}


async def test_acquisition_update_tile(live, seed):
    client = live.client
    tiles = await seed.tiles()
    updated = await client.acquisition.update_tile("A1", tiles[0].tile_id, TileUpdate(focus_score=0.5))
    assert updated.focus_score == 0.5


async def test_acquisition_update_tiles_bulk(live, seed):
    client = live.client
    tiles = await seed.tiles()
    updated = await client.acquisition.update_tiles_bulk(
        "A1",
        {
            tiles[0].tile_id: TileUpdate(focus_score=0.25),
            tiles[1].tile_id: TileUpdate(focus_score=0.75),
        },
    )
    assert {t.tile_id: t.focus_score for t in updated} == {
        tiles[0].tile_id: 0.25,
        tiles[1].tile_id: 0.75,
    }


async def test_acquisition_delete_tile(live, seed):
    client = live.client
    tiles = await seed.tiles()
    await client.acquisition.delete_tile("A1", tiles[0].tile_id)
    with pytest.raises(TEMdbNotFoundError):
        await client.acquisition.get_tile("A1", tiles[0].tile_id)


async def test_acquisition_delete_tiles_bulk(live, seed):
    client = live.client
    tiles = await seed.tiles()
    missing = str(uuid.uuid4())
    result = await client.acquisition.delete_tiles_bulk("A1", [tiles[0].tile_id, missing])
    assert (result.requested, result.deleted, result.not_found) == (2, 1, [missing])


async def test_acquisition_delete_all_tiles(live, seed):
    client = live.client
    await seed.tiles()
    assert (await client.acquisition.delete_all_tiles("A1")).deleted == 10
    assert await client.acquisition.get_tile_count("A1") == {"tile_count": 0}


async def test_complete_metadata_returns_the_acquisition_hierarchy(live, seed):
    acquisition = await seed.acquisition()
    metadata = await live.client.acquisition.get_complete_metadata("A1")
    assert metadata["acquisition"]["acquisition_id"] == "A1"
    assert metadata["roi"]["roi_id"] == acquisition.roi_id
    assert live.unmatched_requests() == []


async def test_list_with_full_metadata_reads_the_aggregated_route(live, seed):
    await seed.acquisition()
    result = await live.client.acquisition.list_with_full_metadata()
    assert [row["acquisition"]["acquisition_id"] for row in result["acquisitions"]] == ["A1"]
    assert (await live.client.acquisition.list_with_full_metadata(roi_id="ROI-NONE"))["acquisitions"] == []
    assert ("GET", "/api/v2/aggregated/acquisitions") in live.transport.requests


async def test_get_tiles_with_fields_returns_projected_tiles(live, seed):
    await seed.tiles()
    page = await live.client.acquisition.get_tiles("A1", fields=["raster_index"])
    assert [tile["raster_index"] for tile in page["tiles"]] == list(range(10))
    assert "image_path" not in page["tiles"][0]


async def test_get_all_tiles_with_fields_follows_every_page(live, seed):
    await seed.tiles()
    tiles = await live.client.acquisition.get_all_tiles("A1", page_limit=3, fields=["raster_index"])
    assert [tile["raster_index"] for tile in tiles] == list(range(10))


async def test_list_with_fields_returns_projected_acquisitions(live, seed):
    await seed.acquisition()
    page = await live.client.acquisition.list(fields=["acquisition_id"])
    assert [row["acquisition_id"] for row in page["acquisitions"]] == ["A1"]


async def test_list_with_full_metadata_rejects_filters_the_route_does_not_read(live, seed):
    await seed.acquisition()
    with pytest.raises(TypeError):
        await live.client.acquisition.list_with_full_metadata(magnification=1000)


async def test_list_with_full_metadata_filters_by_substrate(live, seed):
    await seed.acquisition()
    matching = await live.client.acquisition.list_with_full_metadata(substrate_media_id="M1")
    assert [row["acquisition"]["acquisition_id"] for row in matching["acquisitions"]] == ["A1"]
    assert (await live.client.acquisition.list_with_full_metadata(substrate_media_id="M-NONE"))["acquisitions"] == []


async def test_get_all_tiles_requests_each_page_once(live, seed):
    await seed.tiles()
    tiles_request = ("GET", "/api/v2/acquisitions/A1/tiles")
    for page_limit, pages in ((100, 1), (3, 4)):
        before = live.transport.requests.count(tiles_request)
        await live.client.acquisition.get_all_tiles("A1", page_limit=page_limit)
        assert live.transport.requests.count(tiles_request) - before == pages
