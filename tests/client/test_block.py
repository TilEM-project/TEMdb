import pytest


@pytest.mark.asyncio
async def test_block_list(mock_client):
    mock_client.block.list.return_value = [{"block_id": "BLOCK001"}]
    result = await mock_client.block.list("SPEC001")
    assert result == [{"block_id": "BLOCK001"}]
    mock_client.block.list.assert_called_once_with("SPEC001")


@pytest.mark.asyncio
async def test_block_create(mock_client):
    block_data = {"block_id": "BLOCK002", "specimen_id": "SPEC001"}
    mock_client.block.create.return_value = block_data
    result = await mock_client.block.create(block_data)
    assert result == block_data
    mock_client.block.create.assert_called_once_with(block_data)


@pytest.mark.asyncio
async def test_block_get(mock_client):
    block_data = {"block_id": "BLOCK002", "specimen_id": "SPEC001"}

    mock_client.block.get.return_value = block_data
    result = await mock_client.block.get("SPEC001", "BLOCK002")
    assert result == block_data
    mock_client.block.get.assert_called_once_with("SPEC001", "BLOCK002")


@pytest.mark.asyncio
async def test_block_update(mock_client):
    block_data = {"block_id": "BLOCK002", "specimen_id": "SPEC001"}

    update_data = {"microCT_info": {"resolution": 1.5}}
    mock_client.block.update.return_value = {**block_data, **update_data}
    result = await mock_client.block.update("SPEC001", "BLOCK002", update_data)
    assert result == {**block_data, **update_data}
    mock_client.block.update.assert_called_once_with("SPEC001", "BLOCK002", update_data)


@pytest.mark.asyncio
async def test_block_delete(mock_client):
    await mock_client.block.delete("SPEC001", "BLOCK002")
    mock_client.block.delete.assert_called_once_with("SPEC001", "BLOCK002")
