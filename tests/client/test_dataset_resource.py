import uuid
from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.dataset import DatasetResource
from temdb.models import DatasetCreate, DatasetUpdate

API = "http://test/api/v2"


def _resource():
    request = AsyncMock()
    return DatasetResource(request, API), request


@pytest.mark.asyncio
async def test_create_posts_dataset():
    res, request = _resource()
    request.return_value = {
        "dataset_id": str(uuid.uuid4()), "name": "d1", "status": "collecting",
        "size_class": "small", "tile_hash_modulus": None, "estimated_tile_count": None,
    }
    out = await res.create(DatasetCreate(name="d1", size_class="small"))
    method, endpoint = request.await_args.args[0], request.await_args.args[1]
    assert (method, endpoint) == ("POST", "datasets")
    assert out.name == "d1"


@pytest.mark.asyncio
async def test_get_by_name_uses_by_name_path():
    res, request = _resource()
    request.return_value = {
        "dataset_id": str(uuid.uuid4()), "name": "d1", "status": "collecting", "size_class": "small"
    }
    await res.get_by_name("d1")
    assert request.await_args.args[1] == "datasets/by-name/d1"


@pytest.mark.asyncio
async def test_list_returns_models():
    res, request = _resource()
    request.return_value = [
        {"dataset_id": str(uuid.uuid4()), "name": "a", "status": "collecting", "size_class": "small"},
        {"dataset_id": str(uuid.uuid4()), "name": "b", "status": "collected", "size_class": "large"},
    ]
    out = await res.list(status="collected")
    assert [d.name for d in out] == ["a", "b"]
    assert request.await_args.args[1] == "datasets"


@pytest.mark.asyncio
async def test_update_patches():
    res, request = _resource()
    dataset_id = str(uuid.uuid4())
    request.return_value = {"dataset_id": dataset_id, "name": "a", "status": "archived", "size_class": "small"}
    await res.update("1", DatasetUpdate(status="archived"))
    assert request.await_args.args[0] == "PATCH"
    assert request.await_args.args[1] == "datasets/1"


@pytest.mark.asyncio
async def test_create_with_estimate_total_count():
    res, request = _resource()
    request.return_value = {
        "dataset_id": str(uuid.uuid4()), "name": "d", "status": "collecting",
        "size_class": "medium", "estimated_tile_count": 2_000_000_000,
    }
    await res.create_with_estimate("d", estimated_tile_count=2_000_000_000)
    sent = request.await_args.kwargs["json"]  # BaseResource._post forwards body as json=
    assert sent["estimated_tile_count"] == 2_000_000_000
    assert "size_class" not in sent  # server resolves it


@pytest.mark.asyncio
async def test_create_with_estimate_roi_product():
    res, request = _resource()
    request.return_value = {
        "dataset_id": str(uuid.uuid4()), "name": "d", "status": "collecting",
        "size_class": "medium", "estimated_tile_count": 50_000,
    }
    await res.create_with_estimate("d", estimated_roi_count=500, tiles_per_roi=100)
    assert request.await_args.kwargs["json"]["estimated_tile_count"] == 50_000


@pytest.mark.asyncio
async def test_create_with_estimate_requires_an_input():
    res, _ = _resource()
    with pytest.raises(ValueError):
        await res.create_with_estimate("d")
