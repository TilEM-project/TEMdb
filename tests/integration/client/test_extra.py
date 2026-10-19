from datetime import datetime, timezone

from temdb.models import MicroscopeCreate


async def test_records_created_without_extra_have_an_empty_extra(client, records):
    await records.tiles()
    lens_correction = await client.lens_correction.create(
        microscope_id="scope-1", magnification=1000, started_at=datetime(2026, 3, 1, tzinfo=timezone.utc)
    )
    made = {
        "specimen": await records.specimen(),
        "block": await records.block(),
        "layout": await records.layout(),
        "substrate": await records.substrate(),
        "cutting_session": await records.cutting_session(),
        "section": await records.section(),
        "roi": await records.roi(),
        "task": await records.task(),
        "microscope": await records.microscope(),
        "dataset": await records.dataset(),
        "acquisition": await records.acquisition(),
        "lens_correction": lens_correction,
        "tile": (await records.tiles())[0],
    }
    assert {name: record.extra for name, record in made.items()} == {name: {} for name in made}


async def test_extra_sent_as_null_on_create_is_stored_empty(client):
    created = await client.microscope.create(MicroscopeCreate(microscope_id="scope-null", extra=None))
    assert created.extra == {}
    assert (await client.microscope.get("scope-null")).extra == {}


async def test_an_update_with_extra_null_keeps_extra(client):
    await client.microscope.create(MicroscopeCreate(microscope_id="scope-kept", extra={"a": 1}))
    updated = await client.microscope.update("scope-kept", notes="realigned", extra=None)
    assert updated.extra == {"a": 1}


async def test_removing_the_last_extra_key_leaves_extra_empty(client):
    await client.microscope.create(MicroscopeCreate(microscope_id="scope-emptied", extra={"a": 1}))
    updated = await client.microscope.update("scope-emptied", extra={"a": None})
    assert updated.extra == {}
