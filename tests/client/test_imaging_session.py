import pytest


@pytest.mark.asyncio
async def test_imaging_session_list(mock_client):
    mock_client.imaging_session.list.return_value = [{"session_id": "IMG001"}]
    result = await mock_client.imaging_session.list("SPEC001")
    assert result == [{"session_id": "IMG001"}]
    mock_client.imaging_session.list.assert_called_once_with("SPEC001")


@pytest.mark.asyncio
async def test_imaging_session_create(mock_client):
    session_data = {"session_id": "IMG002", "specimen_id": "SPEC001"}
    mock_client.imaging_session.create.return_value = session_data
    result = await mock_client.imaging_session.create(session_data)
    assert result == session_data
    mock_client.imaging_session.create.assert_called_once_with(session_data)


@pytest.mark.asyncio
async def test_imaging_session_get(mock_client):
    session_data = {"session_id": "IMG002", "specimen_id": "SPEC001"}
    mock_client.imaging_session.get.return_value = session_data
    result = await mock_client.imaging_session.get("IMG002")
    assert result == session_data
    mock_client.imaging_session.get.assert_called_once_with("IMG002")


@pytest.mark.asyncio
async def test_imaging_session_update(mock_client):
    session_data = {"session_id": "IMG002", "specimen_id": "SPEC001"}
    update_data = {"status": "COMPLETED"}
    mock_client.imaging_session.update.return_value = {**session_data, **update_data}
    result = await mock_client.imaging_session.update("IMG002", update_data)
    assert result == {**session_data, **update_data}
    mock_client.imaging_session.update.assert_called_once_with("IMG002", update_data)


@pytest.mark.asyncio
async def test_imaging_session_delete(mock_client):
    await mock_client.imaging_session.delete("IMG002")
    mock_client.imaging_session.delete.assert_called_once_with("IMG002")
