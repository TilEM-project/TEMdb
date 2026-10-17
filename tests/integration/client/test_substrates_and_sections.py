import pytest

from temdb.client.exceptions import TEMdbNotFoundError
from temdb.models import (
    SubstrateApertures,
    SubstrateLayoutCreate,
    SubstrateLayoutUpdate,
)


async def test_substrate_layout_create(live, seed):
    client = live.client
    await client.substrate_layout.create(SubstrateLayoutCreate(layout_id="L-NEW", media_type="wafer"))
    assert (await client.substrate_layout.get("L-NEW")).media_type == "wafer"


async def test_substrate_layout_get(live, seed):
    client = live.client
    await seed.layout()
    assert (await client.substrate_layout.get("L1")).layout_id == "L1"


async def test_substrate_layout_list(live, seed):
    client = live.client
    await seed.layout()
    await client.substrate_layout.create(SubstrateLayoutCreate(layout_id="L2", media_type="wafer"))
    assert {layout.layout_id for layout in await client.substrate_layout.list()} == {
        "L1",
        "L2",
    }
    assert [layout.layout_id for layout in await client.substrate_layout.list(media_type="tape")] == ["L1"]


async def test_substrate_layout_update(live, seed):
    client = live.client
    await seed.layout()
    updated = await client.substrate_layout.update("L1", SubstrateLayoutUpdate(name="renamed"))
    assert updated.name == "renamed"


async def test_substrate_layout_delete(live, seed):
    client = live.client
    await seed.layout()
    await client.substrate_layout.delete("L1")
    with pytest.raises(TEMdbNotFoundError):
        await client.substrate_layout.get("L1")


async def test_substrate_layout_list_related_substrates(live, seed):
    client = live.client
    await seed.substrate()
    await client.substrate_layout.create(SubstrateLayoutCreate(layout_id="L2", media_type="tape"))
    await client.substrate.create(media_id="M2", substrate_layout_id="L2")
    assert [s.media_id for s in await client.substrate_layout.list_related_substrates("L1")] == ["M1"]


async def test_substrate_create(live, seed):
    client = live.client
    await seed.layout()
    await client.substrate.create(media_id="M-NEW", substrate_layout_id="L1")
    assert (await client.substrate.get("M-NEW")).substrate_layout_id == "L1"


async def test_substrate_get(live, seed):
    client = live.client
    await seed.substrate()
    assert (await client.substrate.get("M1")).media_id == "M1"


async def test_substrate_list(live, seed):
    client = live.client
    await seed.substrate()
    await client.substrate_layout.create(SubstrateLayoutCreate(layout_id="L2", media_type="tape"))
    await client.substrate.create(media_id="M2", substrate_layout_id="L2")
    assert {s.media_id for s in await client.substrate.list()} == {"M1", "M2"}
    assert [s.media_id for s in await client.substrate.list(layout_id="L1")] == ["M1"]


async def test_substrate_update(live, seed):
    client = live.client
    await seed.substrate()
    updated = await client.substrate.update("M1", extra={"note": "scratched"})
    assert updated.extra["note"] == "scratched"


async def test_substrate_get_apertures(live, seed):
    client = live.client
    await seed.substrate()
    apertures = await client.substrate.get_apertures("M1")
    assert isinstance(apertures, SubstrateApertures)
    assert apertures.media_id == "M1"
    assert apertures.layout.layout_id == "L1"


async def test_substrate_delete(live, seed):
    client = live.client
    await seed.substrate()
    await client.substrate.delete("M1")
    with pytest.raises(TEMdbNotFoundError):
        await client.substrate.get("M1")


async def test_substrate_list_related_sections(live, seed):
    client = live.client
    section = await seed.section()
    assert [s.section_id for s in await client.substrate.list_related_sections("M1")] == [section.section_id]


async def test_section_create(live, seed):
    client = live.client
    await seed.cutting_session()
    await seed.substrate()
    created = await client.section.create(section_number=2, cutting_session_id="CS1", media_id="M1")
    assert (await client.section.get("CS1", created.section_id)).section_number == 2


async def test_section_get(live, seed):
    client = live.client
    section = await seed.section()
    assert (await client.section.get("CS1", section.section_id)).barcode == "BC1"


async def test_section_list_by_session(live, seed):
    client = live.client
    section = await seed.section()
    assert [s.section_id for s in await client.section.list_by_session("CS1")] == [section.section_id]
    with pytest.raises(TEMdbNotFoundError):
        await client.section.list_by_session("CS-NONE")


async def test_section_list_all(live, seed):
    client = live.client
    section = await seed.section()
    assert [s.section_id for s in await client.section.list_all(cutting_session_id="CS1")] == [section.section_id]
    assert await client.section.list_all(cutting_session_id="CS-NONE") == []


async def test_section_update(live, seed):
    client = live.client
    section = await seed.section()
    updated = await client.section.update("CS1", section.section_id, barcode="BC2")
    assert updated.barcode == "BC2"


async def test_section_delete(live, seed):
    client = live.client
    section = await seed.section()
    await client.section.delete("CS1", section.section_id)
    with pytest.raises(TEMdbNotFoundError):
        await client.section.get("CS1", section.section_id)


async def test_section_list_by_block(live, seed):
    client = live.client
    section = await seed.section()
    assert [s.section_id for s in await client.section.list_by_block("B1")] == [section.section_id]
    assert await client.section.list_by_block("B-NONE") == []


async def test_section_list_by_specimen(live, seed):
    client = live.client
    section = await seed.section()
    assert [s.section_id for s in await client.section.list_by_specimen("SP1")] == [section.section_id]
    assert await client.section.list_by_specimen("SP-NONE") == []


async def test_section_list_by_media(live, seed):
    client = live.client
    section = await seed.section()
    assert [s.section_id for s in await client.section.list_by_media("M1")] == [section.section_id]


async def test_section_list_by_barcode(live, seed):
    client = live.client
    section = await seed.section()
    assert [s.section_id for s in await client.section.list_by_barcode("BC1")] == [section.section_id]
    assert await client.section.list_by_barcode("BC-NONE") == []
