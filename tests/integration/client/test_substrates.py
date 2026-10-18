import pytest

from temdb.client.exceptions import TEMdbNotFoundError
from temdb.models import (
    SubstrateLayoutCreate,
    SubstrateLayoutUpdate,
)


async def test_substrate_layout_create(client, records):
    await client.substrate_layout.create(SubstrateLayoutCreate(layout_id="L-NEW", media_type="wafer"))
    assert (await client.substrate_layout.get("L-NEW")).media_type == "wafer"


async def test_substrate_layout_get(client, records):
    await records.layout()
    assert (await client.substrate_layout.get("GD-9mm-56-G1")).layout_id == "GD-9mm-56-G1"


async def test_substrate_layout_list(client, records):
    await records.layout()
    await client.substrate_layout.create(SubstrateLayoutCreate(layout_id="L2", media_type="wafer"))
    assert {layout.layout_id for layout in await client.substrate_layout.list()} == {
        "GD-9mm-56-G1",
        "L2",
    }
    assert [layout.layout_id for layout in await client.substrate_layout.list(media_type="grid_disc")] == [
        "GD-9mm-56-G1"
    ]


async def test_substrate_layout_update(client, records):
    await records.layout()
    updated = await client.substrate_layout.update("GD-9mm-56-G1", SubstrateLayoutUpdate(name="renamed"))
    assert updated.name == "renamed"


async def test_substrate_layout_delete(client, records):
    await records.layout()
    await client.substrate_layout.delete("GD-9mm-56-G1")
    with pytest.raises(TEMdbNotFoundError):
        await client.substrate_layout.get("GD-9mm-56-G1")


async def test_substrate_layout_list_related_substrates(client, records):
    await records.substrate()
    await client.substrate_layout.create(SubstrateLayoutCreate(layout_id="L2", media_type="grid_disc"))
    await client.substrate.create(media_id="M2", substrate_layout_id="L2")
    assert [s.media_id for s in await client.substrate_layout.list_related_substrates("GD-9mm-56-G1")] == ["M1"]


async def test_substrate_create(client, records):
    await records.layout()
    await client.substrate.create(media_id="M-NEW", substrate_layout_id="GD-9mm-56-G1")
    assert (await client.substrate.get("M-NEW")).substrate_layout_id == "GD-9mm-56-G1"


async def test_substrate_get(client, records):
    await records.substrate()
    assert (await client.substrate.get("M1")).media_id == "M1"


async def test_substrate_list(client, records):
    await records.substrate()
    await client.substrate_layout.create(SubstrateLayoutCreate(layout_id="L2", media_type="grid_disc"))
    await client.substrate.create(media_id="M2", substrate_layout_id="L2")
    assert {s.media_id for s in await client.substrate.list()} == {"M1", "M2"}
    assert [s.media_id for s in await client.substrate.list(layout_id="GD-9mm-56-G1")] == ["M1"]


async def test_substrate_update(client, records):
    await records.substrate()
    updated = await client.substrate.update("M1", extra={"note": "scratched"})
    assert updated.extra["note"] == "scratched"


async def test_substrate_get_apertures(client, records):
    section = await records.section()
    apertures = await client.substrate.get_apertures("M1")
    assert apertures.media_id == "M1"
    assert apertures.layout.layout_id == "GD-9mm-56-G1"
    assert [aperture.index for aperture in apertures.apertures] == list(range(56))
    assert [aperture.sections for aperture in apertures.apertures] == [[section.section_id]] + [[]] * 55


async def test_substrate_delete(client, records):
    await records.substrate()
    await client.substrate.delete("M1")
    with pytest.raises(TEMdbNotFoundError):
        await client.substrate.get("M1")


async def test_substrate_list_related_sections(client, records):
    section = await records.section()
    assert [s.section_id for s in await client.substrate.list_related_sections("M1")] == [section.section_id]
