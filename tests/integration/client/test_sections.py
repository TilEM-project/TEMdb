import inspect
from datetime import datetime, timedelta, timezone

import pytest

from temdb.client.exceptions import TEMdbMissingParentError, TEMdbNotFoundError
from temdb.client.resources.base import BaseResource

PAGE = inspect.signature(BaseResource._list).parameters["page_size"].default


async def test_section_on_a_missing_substrate_raises_missing_parent(client, records):
    await records.cutting_session()

    with pytest.raises(TEMdbMissingParentError) as raised:
        await client.section.create(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), cutting_session_id="CS1", media_id="NO_SUCH_SUBSTRATE"
        )

    assert (raised.value.parent, raised.value.id) == ("substrate", "NO_SUCH_SUBSTRATE")


async def test_section_list_by_media_returns_more_than_one_page(client, records):
    await records.cutting_session()
    await records.substrate()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for minute in range(PAGE + 5):
        await client.section.create(
            timestamp=start + timedelta(minutes=minute), cutting_session_id="CS1", media_id="M1"
        )

    everything = await client.section.list_by_media("M1")
    first_page = await client.section.list_by_media("M1", limit=PAGE)

    assert len(everything) == PAGE + 5
    assert len({section.section_id for section in everything}) == PAGE + 5
    assert len(first_page.items) == PAGE and first_page.next_cursor is not None


async def test_section_create(client, records):
    await records.cutting_session()
    await records.substrate()
    created = await client.section.create(
        timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc), cutting_session_id="CS1", media_id="M1"
    )
    assert (await client.section.get(created.section_id)).section_number == 1


async def test_section_get(client, records):
    section = await records.section()
    assert (await client.section.get(section.section_id)).media_id == "M1"


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
    updated = await client.section.update(section.section_id, cut_count=7)
    assert updated.cut_count == 7


async def test_section_delete(client, records):
    section = await records.section()
    await client.section.delete(section.section_id)
    with pytest.raises(TEMdbNotFoundError):
        await client.section.get(section.section_id)


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
