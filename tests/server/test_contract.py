import importlib.metadata

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_contract_returns_installed_versions(async_client: AsyncClient):
    response = await async_client.get("/api/v2/contract")
    assert response.status_code == 200
    assert response.json() == {
        "api": "v2",
        "server_version": importlib.metadata.version("temdb"),
        "models_version": importlib.metadata.version("temdb-models"),
    }
