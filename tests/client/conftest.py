from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from temdb.client import AsyncTEMdbClient, create_client


@pytest_asyncio.fixture
async def client():
    client = create_client("https://api.temdb.example.com", async_mode=True)
    try:
        yield client
    finally:
        await client.close()


@pytest.fixture
def mock_client():
    mock_client = AsyncMock(spec=AsyncTEMdbClient)
    mock_client.specimen = AsyncMock()
    mock_client.block = AsyncMock()
    mock_client.cutting_session = AsyncMock()
    mock_client.imaging_session = AsyncMock()
    mock_client.roi = AsyncMock()
    mock_client.acquisition = AsyncMock()
    return mock_client
