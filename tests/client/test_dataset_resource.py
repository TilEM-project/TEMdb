import uuid
from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.dataset import DatasetResource
from temdb.models import DatasetCreate

API = "http://test/api/v2"


def _resource():
    request = AsyncMock()
    return DatasetResource(request, API), request


@pytest.mark.asyncio
async def test_create_accepts_kwargs_via_decorator():
    res, request = _resource()
    request.return_value = {
        "dataset_id": str(uuid.uuid4()),
        "name": "d2",
        "status": "collecting",
        "size_class": "small",
    }
    out = await res.create(name="d2", size_class="small")
    assert request.await_args.kwargs["json"] == {"name": "d2", "size_class": "small"}
    assert out.name == "d2"


@pytest.mark.asyncio
async def test_create_rejects_model_plus_kwargs():
    res, _ = _resource()
    with pytest.raises(TypeError):
        await res.create(DatasetCreate(name="d1", size_class="small"), status="collecting")


@pytest.mark.asyncio
async def test_update_accepts_kwargs_via_decorator():
    res, request = _resource()
    dataset_id = str(uuid.uuid4())
    request.return_value = {"dataset_id": dataset_id, "name": "a", "status": "archived", "size_class": "small"}
    out = await res.update("1", status="archived")
    assert request.await_args.kwargs["json"] == {"status": "archived"}
    assert out.status == "archived"


@pytest.mark.asyncio
async def test_create_with_estimate_total_count():
    res, request = _resource()
    request.return_value = {
        "dataset_id": str(uuid.uuid4()),
        "name": "d",
        "status": "collecting",
        "size_class": "medium",
        "estimated_tile_count": 2_000_000_000,
    }
    await res.create_with_estimate("d", estimated_tile_count=2_000_000_000)
    sent = request.await_args.kwargs["json"]  # BaseResource._post forwards body as json=
    assert sent["estimated_tile_count"] == 2_000_000_000
    assert "size_class" not in sent  # server resolves it


@pytest.mark.asyncio
async def test_create_with_estimate_roi_product():
    res, request = _resource()
    request.return_value = {
        "dataset_id": str(uuid.uuid4()),
        "name": "d",
        "status": "collecting",
        "size_class": "medium",
        "estimated_tile_count": 50_000,
    }
    await res.create_with_estimate("d", estimated_roi_count=500, tiles_per_roi=100)
    assert request.await_args.kwargs["json"]["estimated_tile_count"] == 50_000


@pytest.mark.asyncio
async def test_create_with_estimate_requires_an_input():
    res, _ = _resource()
    with pytest.raises(ValueError):
        await res.create_with_estimate("d")
