from datetime import datetime

import pytest


@pytest.mark.asyncio
async def test_list_cutting_sessions(async_client):
    response = await async_client.get("/api/v2/cutting-sessions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_cutting_session(async_client, test_block):
    session_data = {
        "cutting_session_id": "TEST_CUT_CREATE",
        "start_time": datetime.now().isoformat(),
        "operator": "Test Operator Create",
        "sectioning_device": "Test Device Create",
        "media_type": "tape",
        "block_id": test_block.block_id,
    }
    response = await async_client.post("/api/v2/cutting-sessions", json=session_data)
    assert response.status_code == 200
    assert response.json()["cutting_session_id"] == "TEST_CUT_CREATE"


@pytest.mark.asyncio
async def test_get_cutting_session(
    async_client, test_specimen, test_block, test_cutting_session
):
    response = await async_client.get(
        f"/api/v2/cutting-sessions/specimens/{test_specimen.specimen_id}/blocks/{test_block.block_id}/cutting-sessions/{test_cutting_session.cutting_session_id}"
    )
    assert response.status_code == 200
    assert (
        response.json()["cutting_session_id"] == test_cutting_session.cutting_session_id
    )


@pytest.mark.asyncio
async def test_update_cutting_session(async_client, test_cutting_session):
    update_data = {"operator": "Updated Operator"}
    response = await async_client.patch(
        f"/api/v2/cutting-sessions/{test_cutting_session.cutting_session_id}",
        json=update_data,
    )
    assert response.status_code == 200
    assert response.json()["operator"] == "Updated Operator"


@pytest.mark.asyncio
async def test_delete_cutting_session(async_client, test_block):
    # Create a new cutting session for deletion
    session_data = {
        "cutting_session_id": "TEST_CUT_DELETE",
        "start_time": datetime.now().isoformat(),
        "operator": "Test Operator Delete",
        "sectioning_device": "Test Device Delete",
        "media_type": "tape",
        "block_id": test_block.block_id,
    }
    create_response = await async_client.post(
        "/api/v2/cutting-sessions", json=session_data
    )
    assert create_response.status_code == 200

    # Delete the cutting session
    response = await async_client.delete(f"/api/v2/cutting-sessions/TEST_CUT_DELETE")
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_get_cutting_session_sections(
    async_client, test_specimen, test_block, test_cutting_session, test_section
):
    response = await async_client.get(
        f"/api/v2/cutting-sessions/specimens/{test_specimen.specimen_id}/blocks/{test_block.block_id}/cutting-sessions/{test_cutting_session.cutting_session_id}/sections"
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
