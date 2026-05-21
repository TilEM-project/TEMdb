from datetime import datetime

import httpx

from temdb.models import SubstrateCreate, SubstrateUpdate
from temdb.models.substrate import SubstrateMetadata


async def test_create_serializes_datetime_metadata(client, captured, response_queue):
    response_queue.append(
        httpx.Response(200, json={"media_id": "M1", "media_type": "GridDisc"})
    )
    meta = SubstrateMetadata(
        name="wafer1",
        user="xiaoyu",
        created=datetime(2026, 1, 2, 3, 4, 5),
        calibrated=datetime(2026, 1, 2, 3, 4, 6),
    )
    body = SubstrateCreate(media_id="M1", media_type="GridDisc", metadata=meta)

    await client.substrate.create(body)

    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/substrates"
    assert req.body == {
        "media_id": "M1",
        "media_type": "GridDisc",
        "metadata": {
            "name": "wafer1",
            "user": "xiaoyu",
            "created": "2026-01-02T03:04:05",
            "calibrated": "2026-01-02T03:04:06",
        },
    }


async def test_list_sends_filter_params(client, captured):
    await client.substrate.list(media_type="GridDisc", status="new", skip=10, limit=50)
    req = captured[-1]
    assert req.method == "GET"
    assert req.path == "/api/v2/substrates"
    assert req.params == {
        "media_type": "GridDisc",
        "status": "new",
        "skip": "10",
        "limit": "50",
    }


async def test_get_uses_media_id_in_path(client, captured, response_queue):
    response_queue.append(
        httpx.Response(200, json={"media_id": "WAFER-99", "media_type": "GridDisc"})
    )
    await client.substrate.get("WAFER-99")
    req = captured[-1]
    assert req.method == "GET"
    assert req.path == "/api/v2/substrates/WAFER-99"


async def test_update_patches_only_set_fields(client, captured, response_queue):
    response_queue.append(
        httpx.Response(
            200,
            json={"media_id": "WAFER-99", "media_type": "GridDisc", "status": "in_use"},
        )
    )
    await client.substrate.update("WAFER-99", SubstrateUpdate(status="in_use"))
    req = captured[-1]
    assert req.method == "PATCH"
    assert req.path == "/api/v2/substrates/WAFER-99"
    assert req.body == {"status": "in_use"}


async def test_delete_hits_singleton_path(client, captured):
    await client.substrate.delete("WAFER-99")
    req = captured[-1]
    assert req.method == "DELETE"
    assert req.path == "/api/v2/substrates/WAFER-99"


async def test_list_related_sections_path(client, captured):
    await client.substrate.list_related_sections("WAFER-99", skip=5, limit=10)
    req = captured[-1]
    assert req.method == "GET"
    assert req.path == "/api/v2/substrates/WAFER-99/sections"
    assert req.params == {"skip": "5", "limit": "10"}
