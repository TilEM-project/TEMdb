import httpx

from temdb.models import SectionCreate, SectionUpdate
from temdb.models.section import SectionQuality


def _section_resp(section_id: str = "SEC001") -> dict:
    return {
        "section_id": section_id,
        "section_number": 1,
        "cutting_session_id": "CUT001",
        "block_id": "B1",
        "specimen_id": "SPEC001",
        "media_id": "M1",
    }


async def test_create_posts_required_fields(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_section_resp()))
    await client.section.create(
        SectionCreate(cutting_session_id="CUT001", section_number=1, media_id="M1")
    )
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/sections"
    assert req.body == {
        "cutting_session_id": "CUT001",
        "section_number": 1,
        "media_id": "M1",
    }


async def test_list_by_session(client, captured):
    await client.section.list_by_session("CUT001")
    assert captured[-1].path == "/api/v2/sections/sessions/CUT001"


async def test_list_all_with_quality_enum(client, captured):
    await client.section.list_all(quality=SectionQuality.GOOD, limit=10)
    req = captured[-1]
    assert req.path == "/api/v2/sections"
    assert req.params["quality"] == "good"
    assert req.params["limit"] == "10"


async def test_get_nested_path(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_section_resp()))
    await client.section.get("CUT001", "SEC001")
    assert captured[-1].path == "/api/v2/sections/sessions/CUT001/sections/SEC001"


async def test_update_patches(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_section_resp()))
    await client.section.update("CUT001", "SEC001", SectionUpdate(barcode="BC1"))
    req = captured[-1]
    assert req.method == "PATCH"
    assert req.path == "/api/v2/sections/sessions/CUT001/sections/SEC001"
    assert req.body == {"barcode": "BC1"}


async def test_delete(client, captured):
    await client.section.delete("CUT001", "SEC001")
    req = captured[-1]
    assert req.method == "DELETE"
    assert req.path == "/api/v2/sections/sessions/CUT001/sections/SEC001"


async def test_list_by_block(client, captured):
    await client.section.list_by_block("B1")
    assert captured[-1].path == "/api/v2/sections/blocks/B1"


async def test_list_by_media(client, captured):
    await client.section.list_by_media("M1", relative_position=3)
    req = captured[-1]
    assert req.path == "/api/v2/sections/media/M1"
    assert req.params["relative_position"] == "3"


async def test_list_by_barcode(client, captured):
    await client.section.list_by_barcode("BC9")
    assert captured[-1].path == "/api/v2/sections/barcode/BC9"
