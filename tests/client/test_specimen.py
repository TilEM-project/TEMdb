import pytest


@pytest.mark.asyncio
async def test_specimen_list(mock_client):
    mock_client.specimen.list.return_value = [{"specimen_id": "SPEC001"}]
    result = await mock_client.specimen.list()
    assert result == [{"specimen_id": "SPEC001"}]
    mock_client.specimen.list.assert_called_once()


@pytest.mark.asyncio
async def test_specimen_create(mock_client):
    specimen_data = {"specimen_id": "SPEC002", "description": "Test specimen"}
    mock_client.specimen.create.return_value = specimen_data
    result = await mock_client.specimen.create(specimen_data)
    assert result == specimen_data
    mock_client.specimen.create.assert_called_once_with(specimen_data)


@pytest.mark.asyncio
async def test_specimen_get(mock_client):
    specimen_data = {"specimen_id": "SPEC002", "description": "Test specimen"}

    mock_client.specimen.get.return_value = specimen_data
    result = await mock_client.specimen.get("SPEC002")
    assert result == specimen_data
    mock_client.specimen.get.assert_called_once_with("SPEC002")


@pytest.mark.asyncio
async def test_specimen_update(mock_client):
    specimen_data = {"specimen_id": "SPEC002", "description": "Test specimen"}

    update_data = {"description": "Updated description"}
    mock_client.specimen.update.return_value = {**specimen_data, **update_data}
    result = await mock_client.specimen.update("SPEC002", update_data)
    assert result == {**specimen_data, **update_data}
    mock_client.specimen.update.assert_called_once_with("SPEC002", update_data)


@pytest.mark.asyncio
async def test_specimen_delete(mock_client):
    await mock_client.specimen.delete("SPEC002")
    mock_client.specimen.delete.assert_called_once_with("SPEC002")
