from temdb.models import DatasetCreate, DatasetUpdate


async def test_dataset_create(client, records):
    created = await client.dataset.create(DatasetCreate(name="ds-new", estimated_tile_count=10))
    assert (await client.dataset.get(str(created.dataset_id))).name == "ds-new"


async def test_dataset_create_with_estimate(client, records):
    created = await client.dataset.create_with_estimate("ds-est", estimated_tile_count=5000)
    assert created.estimated_tile_count == 5000
    assert created.size_class is not None


async def test_dataset_get(client, records):
    dataset = await records.dataset()
    assert (await client.dataset.get(str(dataset.dataset_id))).name == "ds-1"


async def test_dataset_get_by_name(client, records):
    dataset = await records.dataset()
    assert (await client.dataset.get_by_name("ds-1")).dataset_id == dataset.dataset_id


async def test_dataset_list(client, records):
    await records.dataset()
    await records.specimen()
    await client.dataset.create(DatasetCreate(name="ds-sp1", specimen_id="SP1", estimated_tile_count=10))
    assert {d.name for d in await client.dataset.list()} == {"ds-1", "ds-sp1"}
    assert [d.name for d in await client.dataset.list(specimen_id="SP1")] == ["ds-sp1"]


async def test_dataset_update(client, records):
    dataset = await records.dataset()
    updated = await client.dataset.update(str(dataset.dataset_id), DatasetUpdate(description="first run"))
    assert updated.description == "first run"
