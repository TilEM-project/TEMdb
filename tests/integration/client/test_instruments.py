from datetime import datetime, timezone

from temdb.models import LensCorrectionCreate, MicroscopeCreate


async def test_microscope_create(client, records):
    created = await client.microscope.create(MicroscopeCreate(label="scope-new", location="room 1"))
    assert (await client.microscope.get(str(created.microscope_id))).location == "room 1"


async def test_microscope_get(client, records):
    microscope = await records.microscope()
    assert (await client.microscope.get(str(microscope.microscope_id))).label == "scope-1"
    assert (await client.microscope.get("scope-1")).microscope_id == microscope.microscope_id


async def test_microscope_list(client, records):
    await records.microscope()
    await client.microscope.create(MicroscopeCreate(label="scope-2"))
    assert {m.label for m in await client.microscope.list()} == {"scope-1", "scope-2"}
    assert len(await client.microscope.list(limit=1)) == 1


async def test_microscope_update(client, records):
    microscope = await records.microscope()
    updated = await client.microscope.update(str(microscope.microscope_id), notes="realigned")
    assert updated.notes == "realigned"


async def test_lens_correction_create(client, records):
    microscope = await records.microscope()
    created = await client.lens_correction.create(
        LensCorrectionCreate(
            microscope_id=microscope.microscope_id,
            magnification=1000,
            started_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
    )
    assert (await client.lens_correction.get(str(created.lc_id))).magnification == 1000


async def test_lens_correction_get(client, records):
    microscope = await records.microscope()
    created = await client.lens_correction.create(
        microscope_id=microscope.microscope_id,
        magnification=1000,
        started_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    assert (await client.lens_correction.get(str(created.lc_id))).microscope_id == microscope.microscope_id


async def test_lens_correction_get_current(client, records):
    microscope = await records.microscope()
    for day in (1, 2):
        await client.lens_correction.create(
            microscope_id=microscope.microscope_id,
            magnification=1000,
            started_at=datetime(2026, 3, day, tzinfo=timezone.utc),
        )
    current = await client.lens_correction.get_current(str(microscope.microscope_id), 1000)
    assert current.started_at == datetime(2026, 3, 2, tzinfo=timezone.utc)


async def test_lens_correction_list(client, records):
    microscope = await records.microscope()
    other = await client.microscope.create(MicroscopeCreate(label="scope-2"))
    for scope, magnification in ((microscope, 1000), (microscope, 2000), (other, 2000)):
        await client.lens_correction.create(
            microscope_id=scope.microscope_id,
            magnification=magnification,
            started_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
    assert len(await client.lens_correction.list()) == 3
    listed = await client.lens_correction.list(microscope_id=str(microscope.microscope_id), magnification=2000)
    assert [(lc.microscope_id, lc.magnification) for lc in listed] == [(microscope.microscope_id, 2000)]


async def test_lens_correction_update(client, records):
    microscope = await records.microscope()
    created = await client.lens_correction.create(
        microscope_id=microscope.microscope_id,
        magnification=1000,
        started_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    updated = await client.lens_correction.update(str(created.lc_id), correction_x_uri="file:///lc/x.tiff")
    assert updated.correction_x_uri == "file:///lc/x.tiff"
