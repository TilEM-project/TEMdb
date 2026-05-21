import httpx

from temdb.models import BlockCreate, BlockUpdate


async def test_create_posts_required_fields(client, captured, response_queue):
    response_queue.append(
        httpx.Response(200, json={"specimen_id": "SPEC001", "block_id": "B1"})
    )
    await client.block.create(BlockCreate(specimen_id="SPEC001", block_id="B1"))
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/blocks"
    assert req.body == {"specimen_id": "SPEC001", "block_id": "B1"}


async def test_list_by_specimen_nested_path(client, captured):
    await client.block.list_by_specimen("SPEC001", skip=0, limit=10)
    req = captured[-1]
    assert req.method == "GET"
    assert req.path == "/api/v2/blocks/specimens/SPEC001/blocks"
    assert req.params == {"skip": "0", "limit": "10"}


async def test_list_all_filters_specimen(client, captured):
    await client.block.list_all(specimen_id="SPEC001", limit=5)
    req = captured[-1]
    assert req.path == "/api/v2/blocks"
    assert req.params == {"skip": "0", "limit": "5", "specimen_id": "SPEC001"}


async def test_get_uses_compound_path(client, captured, response_queue):
    response_queue.append(
        httpx.Response(200, json={"specimen_id": "SPEC001", "block_id": "B1"})
    )
    await client.block.get("SPEC001", "B1")
    assert captured[-1].path == "/api/v2/blocks/specimens/SPEC001/blocks/B1"


async def test_update_patches_compound_path(client, captured, response_queue):
    response_queue.append(
        httpx.Response(200, json={"specimen_id": "SPEC001", "block_id": "B1"})
    )
    await client.block.update(
        "SPEC001", "B1", BlockUpdate(microCT_info={"resolution": 1.0})
    )
    req = captured[-1]
    assert req.method == "PATCH"
    assert req.path == "/api/v2/blocks/specimens/SPEC001/blocks/B1"
    assert req.body == {"microCT_info": {"resolution": 1.0}}


async def test_delete_compound_path(client, captured):
    await client.block.delete("SPEC001", "B1")
    req = captured[-1]
    assert req.method == "DELETE"
    assert req.path == "/api/v2/blocks/specimens/SPEC001/blocks/B1"


async def test_get_cut_sessions_path(client, captured):
    await client.block.get_cut_sessions("SPEC001", "B1")
    assert (
        captured[-1].path == "/api/v2/blocks/specimens/SPEC001/blocks/B1/cut-sessions"
    )
