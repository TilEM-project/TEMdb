from datetime import datetime, timezone

import pytest

from temdb.client.exceptions import TEMdbNotFoundError


async def test_specimen_create(client, records):
    await client.specimen.create(specimen_id="SP-NEW", description="new")
    assert (await client.specimen.get("SP-NEW")).description == "new"


async def test_specimen_get(client, records):
    await records.specimen()
    assert (await client.specimen.get("SP1")).specimen_id == "SP1"


async def test_specimen_list(client, records):
    await records.specimen()
    await client.specimen.create(specimen_id="SP2", description="other")
    assert {s.specimen_id for s in await client.specimen.list()} == {"SP1", "SP2"}
    assert [s.specimen_id for s in await client.specimen.list(search="other")] == ["SP2"]


async def test_specimen_update(client, records):
    await records.specimen()
    await client.specimen.update("SP1", description="changed")
    assert (await client.specimen.get("SP1")).description == "changed"


async def test_specimen_delete(client, records):
    await records.specimen()
    await client.specimen.delete("SP1")
    with pytest.raises(TEMdbNotFoundError):
        await client.specimen.get("SP1")


async def test_specimen_list_blocks(client, records):
    await records.block()
    assert [b.block_id for b in await client.specimen.list_blocks("SP1")] == ["B1"]


async def test_block_create(client, records):
    await records.specimen()
    await client.block.create(block_id="B2", specimen_id="SP1")
    assert (await client.block.get("SP1", "B2")).block_id == "B2"


async def test_block_get(client, records):
    await records.block()
    assert (await client.block.get("SP1", "B1")).specimen_id == "SP1"


async def test_block_list_by_specimen(client, records):
    await records.block()
    await client.specimen.create(specimen_id="SP2")
    await client.block.create(block_id="B9", specimen_id="SP2")
    assert [b.block_id for b in await client.block.list_by_specimen("SP1")] == ["B1"]


async def test_block_list_all(client, records):
    await records.block()
    await client.specimen.create(specimen_id="SP2")
    await client.block.create(block_id="B9", specimen_id="SP2")
    assert {b.block_id for b in await client.block.list_all()} == {"B1", "B9"}
    assert [b.block_id for b in await client.block.list_all(specimen_id="SP1")] == ["B1"]


async def test_block_update(client, records):
    await records.block()
    await client.block.update("SP1", "B1", description="trimmed")
    assert (await client.block.get("SP1", "B1")).description == "trimmed"


async def test_block_delete(client, records):
    await records.block()
    await client.block.delete("SP1", "B1")
    with pytest.raises(TEMdbNotFoundError):
        await client.block.get("SP1", "B1")


async def test_block_get_cut_sessions(client, records):
    await records.cutting_session()
    assert [s.cutting_session_id for s in await client.block.get_cut_sessions("SP1", "B1")] == ["CS1"]


async def test_cutting_session_create(client, records):
    await records.block()
    await client.cutting_session.create(
        cutting_session_id="CS2",
        block_id="B1",
        start_time=datetime(2026, 2, 1, tzinfo=timezone.utc),
        sectioning_device="robot",
        media_type="grid_disc",
    )
    assert (await client.cutting_session.get("SP1", "B1", "CS2")).cutting_session_id == "CS2"


async def test_cutting_session_get(client, records):
    await records.cutting_session()
    assert (await client.cutting_session.get("SP1", "B1", "CS1")).block_id == "B1"


async def test_cutting_session_list_by_block(client, records):
    await records.cutting_session()
    await client.block.create(block_id="B2", specimen_id="SP1")
    await client.cutting_session.create(
        cutting_session_id="CS9",
        block_id="B2",
        start_time=datetime(2026, 2, 1, tzinfo=timezone.utc),
        sectioning_device="robot",
        media_type="grid_disc",
    )
    assert [s.cutting_session_id for s in await client.cutting_session.list_by_block("SP1", "B1")] == ["CS1"]


async def test_cutting_session_list_all(client, records):
    await records.cutting_session()
    await client.cutting_session.create(
        cutting_session_id="CS2",
        block_id="B1",
        start_time=datetime(2026, 2, 1, tzinfo=timezone.utc),
        sectioning_device="robot",
        media_type="grid_disc",
        operator="ann",
    )
    assert {s.cutting_session_id for s in await client.cutting_session.list_all()} == {
        "CS1",
        "CS2",
    }
    assert [s.cutting_session_id for s in await client.cutting_session.list_all(operator="ann")] == ["CS2"]


async def test_cutting_session_update(client, records):
    await records.cutting_session()
    updated = await client.cutting_session.update("CS1", operator="bob")
    assert updated.operator == "bob"


async def test_cutting_session_delete(client, records):
    await records.cutting_session()
    await client.cutting_session.delete("CS1")
    with pytest.raises(TEMdbNotFoundError):
        await client.cutting_session.get("SP1", "B1", "CS1")


async def test_cutting_session_list_sections(client, records):
    section = await records.section()
    listed = await client.cutting_session.list_sections("SP1", "B1", "CS1")
    assert [s.section_id for s in listed] == [section.section_id]
