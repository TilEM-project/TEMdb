import pytest

from temdb.client.exceptions import NotFoundError
from tests.client_integration.generators import generate_specimen


@pytest.mark.asyncio
@pytest.mark.parametrize("created_at", (..., None))
@pytest.mark.parametrize("specimen_images", (..., None, []))
async def test_specimen(async_client, created_at, specimen_images):
    kwargs = {}
    if created_at is not ...:
        kwargs["created_at"] = created_at
    if specimen_images is not ...:
        kwargs["specimen_images"] = specimen_images
    specimen = generate_specimen(**kwargs)
    old_specimens = await async_client.specimen.list()
    await async_client.specimen.create(specimen)
    specimens = await async_client.specimen.list()
    assert len(old_specimens) + 1 == len(specimens)
    async_client.specimen.get(specimen.specimen_id)
    await async_client.specimen.delete(specimen.specimen_id)
    specimens = await async_client.specimen.list()
    assert old_specimens == specimens
    with pytest.raises(NotFoundError):
        await async_client.specimen.get(specimen.specimen_id)
