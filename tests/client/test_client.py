from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from temdb.client import TEMdbClient
from temdb.models import SpecimenCreate


@pytest.mark.asyncio
async def test_client_initialization(client):
    assert isinstance(client, TEMdbClient)


@pytest.mark.asyncio
async def test_resource_creation(client):
    assert hasattr(client, "specimen")
    assert hasattr(client, "block")
    assert hasattr(client, "cutting_session")
    assert hasattr(client, "substrate")
    assert hasattr(client, "acquisition_task")
    assert hasattr(client, "roi")
    assert hasattr(client, "acquisition")


@pytest.mark.asyncio
async def test_extra_datetime(client):
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"specimen_id": "test"}

    client._http_client.request = AsyncMock(return_value=mock_response)
    await client.specimen.create(
        SpecimenCreate(
            specimen_id="test",
            random_extra_datetime=datetime.now(),
        )
    )
