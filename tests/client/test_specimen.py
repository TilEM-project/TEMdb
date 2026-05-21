import httpx

from temdb.models import SpecimenCreate, SpecimenUpdate


async def test_create_posts_minimal_body(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={"specimen_id": "SPEC001"}))
    await client.specimen.create(SpecimenCreate(specimen_id="SPEC001", description="d"))
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/specimens"
    assert req.body == {"specimen_id": "SPEC001", "description": "d"}


async def test_list_sends_pagination(client, captured):
    await client.specimen.list(skip=5, limit=20)
    req = captured[-1]
    assert req.method == "GET"
    assert req.path == "/api/v2/specimens"
    assert req.params == {"skip": "5", "limit": "20"}


async def test_get_path(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={"specimen_id": "SPEC001"}))
    await client.specimen.get("SPEC001")
    assert captured[-1].path == "/api/v2/specimens/SPEC001"


async def test_update_patches_subset(client, captured, response_queue):
    response_queue.append(
        httpx.Response(200, json={"specimen_id": "SPEC001", "description": "new"})
    )
    await client.specimen.update("SPEC001", SpecimenUpdate(description="new"))
    req = captured[-1]
    assert req.method == "PATCH"
    assert req.path == "/api/v2/specimens/SPEC001"
    assert req.body == {"description": "new"}


async def test_delete_path(client, captured):
    await client.specimen.delete("SPEC001")
    req = captured[-1]
    assert req.method == "DELETE"
    assert req.path == "/api/v2/specimens/SPEC001"


async def test_add_image_posts_image_url(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json={"specimen_id": "SPEC001"}))
    await client.specimen.add_image("SPEC001", "http://img.example/1.png")
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/specimens/SPEC001/images"
    assert req.body == {"image_url": "http://img.example/1.png"}


async def test_list_blocks_nested_path(client, captured):
    await client.specimen.list_blocks("SPEC001", skip=1, limit=2)
    req = captured[-1]
    assert req.path == "/api/v2/specimens/SPEC001/blocks"
    assert req.params == {"skip": "1", "limit": "2"}
