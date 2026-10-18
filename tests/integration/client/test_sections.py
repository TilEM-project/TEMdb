import pytest

from temdb.client.exceptions import TEMdbNotFoundError


async def test_section_create(client, records):
    await records.cutting_session()
    await records.substrate()
    created = await client.section.create(section_number=2, cutting_session_id="CS1", media_id="M1")
    assert (await client.section.get("CS1", created.section_id)).section_number == 2


async def test_section_get(client, records):
    section = await records.section()
    assert (await client.section.get("CS1", section.section_id)).barcode == "BC1"


async def test_section_list_by_session(client, records):
    section = await records.section()
    assert [s.section_id for s in await client.section.list_by_session("CS1")] == [section.section_id]
    with pytest.raises(TEMdbNotFoundError):
        await client.section.list_by_session("CS-NONE")


async def test_section_list_all(client, records):
    section = await records.section()
    assert [s.section_id for s in await client.section.list_all(cutting_session_id="CS1")] == [section.section_id]
    assert await client.section.list_all(cutting_session_id="CS-NONE") == []


async def test_section_update(client, records):
    section = await records.section()
    updated = await client.section.update("CS1", section.section_id, barcode="BC2")
    assert updated.barcode == "BC2"


async def test_section_delete(client, records):
    section = await records.section()
    await client.section.delete("CS1", section.section_id)
    with pytest.raises(TEMdbNotFoundError):
        await client.section.get("CS1", section.section_id)


async def test_section_list_by_block(client, records):
    section = await records.section()
    assert [s.section_id for s in await client.section.list_by_block("B1")] == [section.section_id]
    assert await client.section.list_by_block("B-NONE") == []


async def test_section_list_by_specimen(client, records):
    section = await records.section()
    assert [s.section_id for s in await client.section.list_by_specimen("SP1")] == [section.section_id]
    assert await client.section.list_by_specimen("SP-NONE") == []


async def test_section_list_by_media(client, records):
    section = await records.section()
    assert [s.section_id for s in await client.section.list_by_media("M1")] == [section.section_id]


async def test_section_list_by_barcode(client, records):
    section = await records.section()
    assert [s.section_id for s in await client.section.list_by_barcode("BC1")] == [section.section_id]
    assert await client.section.list_by_barcode("BC-NONE") == []
