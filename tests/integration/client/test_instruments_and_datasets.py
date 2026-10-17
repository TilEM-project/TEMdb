from datetime import datetime, timezone

from temdb.models import (
    DatasetCreate,
    DatasetUpdate,
    LensCorrectionCreate,
    MicroscopeCreate,
)


async def test_microscope_create(live, seed):
    client = live.client
    created = await client.microscope.create(MicroscopeCreate(label="scope-new", location="room 1"))
    assert (await client.microscope.get(str(created.microscope_id))).location == "room 1"


async def test_microscope_get(live, seed):
    client = live.client
    microscope = await seed.microscope()
    assert (await client.microscope.get(str(microscope.microscope_id))).label == "scope-1"
    assert (await client.microscope.get("scope-1")).microscope_id == microscope.microscope_id


async def test_microscope_list(live, seed):
    client = live.client
    await seed.microscope()
    await client.microscope.create(MicroscopeCreate(label="scope-2"))
    assert {m.label for m in await client.microscope.list()} == {"scope-1", "scope-2"}
    assert len(await client.microscope.list(limit=1)) == 1


async def test_microscope_update(live, seed):
    client = live.client
    microscope = await seed.microscope()
    updated = await client.microscope.update(str(microscope.microscope_id), notes="realigned")
    assert updated.notes == "realigned"


async def test_dataset_create(live, seed):
    client = live.client
    created = await client.dataset.create(DatasetCreate(name="ds-new", estimated_tile_count=10))
    assert (await client.dataset.get(str(created.dataset_id))).name == "ds-new"


async def test_dataset_create_with_estimate(live, seed):
    client = live.client
    created = await client.dataset.create_with_estimate("ds-est", estimated_tile_count=5000)
    assert created.estimated_tile_count == 5000
    assert created.size_class is not None


async def test_dataset_get(live, seed):
    client = live.client
    dataset = await seed.dataset()
    assert (await client.dataset.get(str(dataset.dataset_id))).name == "ds-1"


async def test_dataset_get_by_name(live, seed):
    client = live.client
    dataset = await seed.dataset()
    assert (await client.dataset.get_by_name("ds-1")).dataset_id == dataset.dataset_id


async def test_dataset_list(live, seed):
    client = live.client
    await seed.dataset()
    await seed.specimen()
    await client.dataset.create(DatasetCreate(name="ds-sp1", specimen_id="SP1", estimated_tile_count=10))
    assert {d.name for d in await client.dataset.list()} == {"ds-1", "ds-sp1"}
    assert [d.name for d in await client.dataset.list(specimen_id="SP1")] == ["ds-sp1"]


async def test_dataset_update(live, seed):
    client = live.client
    dataset = await seed.dataset()
    updated = await client.dataset.update(str(dataset.dataset_id), DatasetUpdate(description="first run"))
    assert updated.description == "first run"


async def test_lens_correction_create(live, seed):
    client = live.client
    microscope = await seed.microscope()
    created = await client.lens_correction.create(
        LensCorrectionCreate(
            microscope_id=microscope.microscope_id,
            magnification=1000,
            started_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        )
    )
    assert (await client.lens_correction.get(str(created.lc_id))).magnification == 1000


async def test_lens_correction_get(live, seed):
    client = live.client
    microscope = await seed.microscope()
    created = await client.lens_correction.create(
        microscope_id=microscope.microscope_id,
        magnification=1000,
        started_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    assert (await client.lens_correction.get(str(created.lc_id))).microscope_id == microscope.microscope_id


async def test_lens_correction_get_current(live, seed):
    client = live.client
    microscope = await seed.microscope()
    for day in (1, 2):
        await client.lens_correction.create(
            microscope_id=microscope.microscope_id,
            magnification=1000,
            started_at=datetime(2026, 3, day, tzinfo=timezone.utc),
        )
    current = await client.lens_correction.get_current(str(microscope.microscope_id), 1000)
    assert current.started_at == datetime(2026, 3, 2, tzinfo=timezone.utc)


async def test_lens_correction_list(live, seed):
    client = live.client
    microscope = await seed.microscope()
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


async def test_lens_correction_update(live, seed):
    client = live.client
    microscope = await seed.microscope()
    created = await client.lens_correction.create(
        microscope_id=microscope.microscope_id,
        magnification=1000,
        started_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    updated = await client.lens_correction.update(str(created.lc_id), correction_x_uri="file:///lc/x.zarr")
    assert updated.correction_x_uri == "file:///lc/x.zarr"
