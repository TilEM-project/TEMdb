from datetime import datetime

import httpx

from temdb.models import CuttingSessionCreate, CuttingSessionUpdate


def _cs_resp(cs_id: str = "CUT001") -> dict:
    return {
        "cutting_session_id": cs_id,
        "specimen_id": "SPEC001",
        "block_id": "B1",
        "start_time": "2026-01-02T03:04:05",
        "sectioning_device": "dev",
        "media_type": "tape",
    }


async def test_create_serializes_start_time_datetime(client, captured, response_queue):
    """create() uses model_dump(mode='json') — verify datetime becomes ISO string."""
    response_queue.append(httpx.Response(200, json=_cs_resp()))
    body = CuttingSessionCreate(
        cutting_session_id="CUT001",
        block_id="B1",
        start_time=datetime(2026, 1, 2, 3, 4, 5),
        sectioning_device="dev",
        media_type="tape",
    )
    await client.cutting_session.create(body)
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/cutting-sessions"
    assert req.body == {
        "cutting_session_id": "CUT001",
        "block_id": "B1",
        "start_time": "2026-01-02T03:04:05",
        "sectioning_device": "dev",
        "media_type": "tape",
    }


async def test_list_by_block_nested_path(client, captured):
    await client.cutting_session.list_by_block("SPEC001", "B1")
    req = captured[-1]
    assert req.path == "/api/v2/cutting-sessions/specimens/SPEC001/blocks/B1/sessions"


async def test_list_all_with_filters(client, captured):
    await client.cutting_session.list_all(specimen_id="SPEC001", operator="op")
    req = captured[-1]
    assert req.path == "/api/v2/cutting-sessions"
    assert req.params == {
        "skip": "0",
        "limit": "100",
        "specimen_id": "SPEC001",
        "operator": "op",
    }


async def test_get_compound_path(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_cs_resp()))
    await client.cutting_session.get("SPEC001", "B1", "CUT001")
    assert (
        captured[-1].path
        == "/api/v2/cutting-sessions/specimens/SPEC001/blocks/B1/sessions/CUT001"
    )


async def test_update_patches_session(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_cs_resp()))
    await client.cutting_session.update("CUT001", CuttingSessionUpdate(operator="op2"))
    req = captured[-1]
    assert req.method == "PATCH"
    assert req.path == "/api/v2/cutting-sessions/CUT001"
    assert req.body == {"operator": "op2"}


async def test_delete(client, captured):
    await client.cutting_session.delete("CUT001")
    req = captured[-1]
    assert req.method == "DELETE"
    assert req.path == "/api/v2/cutting-sessions/CUT001"


async def test_list_sections(client, captured):
    await client.cutting_session.list_sections("SPEC001", "B1", "CUT001")
    assert (
        captured[-1].path
        == "/api/v2/cutting-sessions/specimens/SPEC001/blocks/B1/sessions/CUT001/sections"
    )
