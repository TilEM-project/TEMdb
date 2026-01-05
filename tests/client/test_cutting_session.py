import datetime

import pytest


@pytest.mark.asyncio
async def test_cutting_session_list(mock_client):
    mock_client.cutting_session.list.return_value = [{"session_id": "CUT001"}]
    result = await mock_client.cutting_session.list("SPEC001", "BLOCK001")
    assert result == [{"session_id": "CUT001"}]
    mock_client.cutting_session.list.assert_called_once_with("SPEC001", "BLOCK001")


@pytest.mark.asyncio
async def test_cutting_session_create(mock_client):
    session_data = {"cutting_session_id": "CUT002", "block_id": "BLOCK001"}
    mock_client.cutting_session.create.return_value = session_data
    result = await mock_client.cutting_session.create(session_data)
    assert result == session_data
    mock_client.cutting_session.create.assert_called_once_with(session_data)


@pytest.mark.asyncio
async def test_cutting_session_get(mock_client):
    session_data = {"cutting_session_id": "CUT002", "block_id": "BLOCK001"}

    mock_client.cutting_session.get.return_value = session_data
    result = await mock_client.cutting_session.get("SPEC001", "BLOCK001", "CUT002")
    assert result == session_data
    mock_client.cutting_session.get.assert_called_once_with("SPEC001", "BLOCK001", "CUT002")


@pytest.mark.asyncio
async def test_cutting_session_update(mock_client):
    session_data = {"cutting_session_id": "CUT002", "block_id": "BLOCK001"}

    update_data = {"end_time": datetime.datetime.now().isoformat()}
    mock_client.cutting_session.update.return_value = {**session_data, **update_data}
    result = await mock_client.cutting_session.update("CUT002", update_data)
    assert result == {**session_data, **update_data}
    mock_client.cutting_session.update.assert_called_once_with("CUT002", update_data)


@pytest.mark.asyncio
async def test_cutting_session_delete(mock_client):
    await mock_client.cutting_session.delete("CUT002")
    mock_client.cutting_session.delete.assert_called_once_with("CUT002")
