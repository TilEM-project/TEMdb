from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_cutting_sessions(async_client: AsyncClient):
    """Test retrieving a list of all cutting sessions."""
    response = await async_client.get("/api/v2/cutting-sessions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_list_cutting_sessions_filtered(
    async_client: AsyncClient, test_specimen, test_block, test_cutting_session
):
    """Test retrieving cutting sessions filtered by parent IDs."""
    response_block = await async_client.get(f"/api/v2/cutting-sessions?block_id={test_block.block_id}")
    assert response_block.status_code == 200
    response_block_data = response_block.json()
    assert isinstance(response_block_data, list)
    assert len(response_block_data) >= 1
    for session in response_block_data:
        assert session["block_id"] == test_block.block_id

    response_specimen = await async_client.get(f"/api/v2/cutting-sessions?specimen_id={test_specimen.specimen_id}")
    assert response_specimen.status_code == 200
    response_specimen_data = response_specimen.json()
    assert isinstance(response_specimen_data, list)
    assert len(response_specimen_data) >= 1
    for session in response_specimen_data:
        assert session["specimen_id"] == test_specimen.specimen_id


@pytest.mark.asyncio
async def test_create_cutting_session(async_client: AsyncClient, test_specimen, test_block):
    """Test creating a new cutting session."""
    emoji_string = "🐀5237 ⬛824⬅️ 🔪12"
    # session_id_hr = (
    #     f"TEST_CUT_CREATE_{int(datetime.now(timezone.utc).timestamp())}"  # Unique ID
    # )
    session_data = {
        "cutting_session_id": emoji_string,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "operator": "Test Operator Create",
        "sectioning_device": "Test Device Create",
        "media_type": "tape",
        "block_id": test_block.block_id,
    }
    response = await async_client.post("/api/v2/cutting-sessions", json=session_data)
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["cutting_session_id"] == emoji_string
    assert response_data["block_id"] == test_block.block_id

    assert response_data["specimen_id"] == test_specimen.specimen_id

    assert response_data["block_ref"]["id"] == str(test_block.id)
    assert response_data["specimen_ref"]["id"] == str(test_specimen.id)


@pytest.mark.asyncio
async def test_get_cutting_session(async_client: AsyncClient, test_specimen, test_block, test_cutting_session):
    """Test retrieving a specific cutting session by human-readable IDs."""
    path = (
        f"/api/v2/cutting-sessions/specimens/{test_specimen.specimen_id}"
        f"/blocks/{test_block.block_id}/sessions/{test_cutting_session.cutting_session_id}"
    )
    response = await async_client.get(path)
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["cutting_session_id"] == test_cutting_session.cutting_session_id
    assert response_data["block_id"] == test_block.block_id
    assert response_data["specimen_id"] == test_specimen.specimen_id
    assert response_data["_id"] == str(test_cutting_session.id)


@pytest.mark.asyncio
async def test_get_cutting_session_not_found(async_client: AsyncClient, test_specimen, test_block):
    """Test retrieving a non-existent cutting session."""
    path = (
        f"/api/v2/cutting-sessions/specimens/{test_specimen.specimen_id}"
        f"/blocks/{test_block.block_id}/sessions/NON_EXISTENT_SESSION"
    )
    response = await async_client.get(path)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_cutting_session(async_client: AsyncClient, test_cutting_session):
    """Test updating a cutting session's operator."""
    update_data = {"operator": "Updated Operator Name"}
    response = await async_client.patch(
        f"/api/v2/cutting-sessions/{test_cutting_session.cutting_session_id}",
        json=update_data,
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["operator"] == "Updated Operator Name"
    assert response_data["cutting_session_id"] == test_cutting_session.cutting_session_id


@pytest.mark.asyncio
async def test_delete_cutting_session(async_client: AsyncClient, test_block):
    """Test deleting a cutting session successfully (when it has no dependencies)."""
    session_id_hr = f"TEST_CUT_DELETE_{int(datetime.now(timezone.utc).timestamp())}"
    session_data = {
        "cutting_session_id": session_id_hr,
        "start_time": datetime.now(timezone.utc).isoformat(),
        "operator": "Test Operator Delete",
        "sectioning_device": "Test Device Delete",
        "media_type": "tape",
        "block_id": test_block.block_id,
    }
    create_response = await async_client.post("/api/v2/cutting-sessions", json=session_data)
    assert create_response.status_code == 201

    delete_response = await async_client.delete(f"/api/v2/cutting-sessions/{session_id_hr}")
    assert delete_response.status_code == 204, delete_response.text

    path = (
        f"/api/v2/cutting-sessions/specimens/{test_block.specimen_id}"
        f"/blocks/{test_block.block_id}/sessions/{session_id_hr}"
    )
    get_response = await async_client.get(path)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_cutting_session_with_sections(async_client: AsyncClient, test_cutting_session, test_section):
    """Test that deleting a cutting session fails if it has associated sections."""
    response = await async_client.delete(f"/api/v2/cutting-sessions/{test_cutting_session.cutting_session_id}")
    assert response.status_code == 400
    response_data = response.json()
    assert "detail" in response_data
    assert "associated sections" in response_data["detail"].lower()


@pytest.mark.asyncio
async def test_get_cutting_session_sections(
    async_client: AsyncClient,
    test_specimen,
    test_block,
    test_cutting_session,
    test_section,
):
    """Test retrieving sections associated with a specific cutting session."""
    path = (
        f"/api/v2/cutting-sessions/specimens/{test_specimen.specimen_id}"
        f"/blocks/{test_block.block_id}/sessions/{test_cutting_session.cutting_session_id}/sections"
    )
    response = await async_client.get(path)
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    assert response_data[0]["cutting_session_id"] == test_cutting_session.cutting_session_id
    assert response_data[0]["section_id"] == test_section.section_id
    # assert response_data[0]["cutting_session_ref"]["$id"] == str(test_cutting_session.id)
