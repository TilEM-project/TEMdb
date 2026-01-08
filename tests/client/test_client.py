import pytest

from temdb.client import AsyncTEMdbClient, SyncTEMdbClient, create_client
from temdb.client.resources.montage import MontageResource
from temdb.client.resources.sync_wrappers.montage import SyncMontageResourceWrapper


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


def test_async_client_has_montage_resource():
    """Test that async client exposes montage resource."""
    client = AsyncTEMdbClient("http://localhost:8000")
    assert hasattr(client, "montage")
    assert isinstance(client.montage, MontageResource)


def test_sync_client_has_montage_resource():
    """Test that sync client exposes montage resource."""
    client = SyncTEMdbClient("http://localhost:8000")
    assert hasattr(client, "montage")
    assert isinstance(client.montage, SyncMontageResourceWrapper)


def test_create_client_async_has_montage():
    """Test create_client factory returns client with montage resource."""
    client = create_client("http://localhost:8000", async_mode=True)
    assert hasattr(client, "montage")


def test_create_client_sync_has_montage():
    """Test create_client factory returns sync client with montage resource."""
    client = create_client("http://localhost:8000", async_mode=False)
    assert hasattr(client, "montage")
