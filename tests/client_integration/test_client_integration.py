import pytest

from temdb.client.exceptions import NotFoundError
from tests.client_integration.generators import generate_block, generate_cutting_session, generate_specimen


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


@pytest.mark.asyncio
@pytest.mark.parametrize("microCT_info", (..., None))
async def test_block(async_client, specimen, microCT_info):
    kwargs = {}
    if microCT_info is not ...:
        kwargs["microCT_info"] = microCT_info
    block = generate_block(specimen.specimen_id, **kwargs)
    old_blocks = await async_client.block.list_all()
    await async_client.block.create(block)
    blocks = await async_client.block.list_all()
    assert len(old_blocks) + 1 == len(blocks)
    async_client.block.get(specimen.specimen_id, block.block_id)
    await async_client.block.delete(specimen.specimen_id, block.block_id)
    blocks = await async_client.block.list_all()
    assert old_blocks == blocks
    with pytest.raises(NotFoundError):
        await async_client.block.get(specimen.specimen_id, block.block_id)


@pytest.mark.asyncio
async def test_cutting_session(async_client, block):
    cutting_session = generate_cutting_session(block.specimen_id, block.block_id)
    old_cutting_sessions = await async_client.cutting_session.list_all()
    await async_client.cutting_session.create(cutting_session)
    cutting_sessions = await async_client.cutting_session.list_all()
    assert len(old_cutting_sessions) + 1 == len(cutting_sessions)
    async_client.cutting_session.get(block.specimen_id, block.block_id, cutting_session.cutting_session_id)
    await async_client.cutting_session.delete(block.specimen_id, block.block_id, cutting_session.cutting_session_id)
    cutting_sessions = await async_client.cutting_sessions.list_all()
    assert old_cutting_sessions == cutting_sessions
    with pytest.raises(NotFoundError):
        await async_client.cutting_session.get(block.specimen_id, block.block_id, cutting_session.cutting_session_id)
