import pytest
from temdb.client import AsyncTEMdbClient


@pytest.mark.asyncio
async def test_client_initialization(client):
    assert isinstance(client, AsyncTEMdbClient)


@pytest.mark.asyncio
async def test_resource_creation(client):
    assert hasattr(client, "specimen")
    assert hasattr(client, "block")
    assert hasattr(client, "cutting_session")
    assert hasattr(client, "substrate")
    assert hasattr(client, "acquisition_task")
    assert hasattr(client, "roi")
    assert hasattr(client, "acquisition")
