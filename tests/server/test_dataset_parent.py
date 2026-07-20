import uuid

import pytest
from httpx import AsyncClient

from temdb.server.ids import uuid7

DS_PAYLOAD = {"size_class": "small"}


async def _create_dataset(async_client: AsyncClient, name: str, **extra) -> dict:
    resp = await async_client.post("/api/v2/datasets", json={**DS_PAYLOAD, "name": name, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _tile_payload() -> dict:
    tile_id = str(uuid7())
    return {
        "tile_id": tile_id,
        "raster_index": 0,
        "stage_position": {"x": 1.0, "y": 2.0},
        "raster_position": {"row": 0, "col": 0},
        "focus_score": 0.9,
        "min_value": 0,
        "max_value": 255,
        "mean_value": 128,
        "std_value": 25,
        "image_path": f"/path/to/{tile_id}.tif",
    }


@pytest.mark.asyncio
async def test_parent_child_lifecycle(async_client: AsyncClient):
    parent = await _create_dataset(async_client, "brain-x")
    assert parent["parent_dataset_id"] is None

    child = await _create_dataset(async_client, "brain-x-left", parent_dataset_id=parent["dataset_id"])
    assert child["parent_dataset_id"] == parent["dataset_id"]

    fetched = await async_client.get(f"/api/v2/datasets/{child['dataset_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["parent_dataset_id"] == parent["dataset_id"]

    children = await async_client.get(f"/api/v2/datasets/{parent['dataset_id']}/children")
    assert children.status_code == 200
    assert [c["dataset_id"] for c in children.json()] == [child["dataset_id"]]


@pytest.mark.asyncio
async def test_list_datasets_filters_by_parent(async_client: AsyncClient):
    parent = await _create_dataset(async_client, "brain-y")
    child = await _create_dataset(async_client, "brain-y-right", parent_dataset_id=parent["dataset_id"])
    await _create_dataset(async_client, "unrelated")

    listed = await async_client.get("/api/v2/datasets", params={"parent_dataset_id": parent["dataset_id"]})
    assert listed.status_code == 200
    assert [d["dataset_id"] for d in listed.json()] == [child["dataset_id"]]


@pytest.mark.asyncio
async def test_grandchild_rejected(async_client: AsyncClient):
    parent = await _create_dataset(async_client, "brain-z")
    child = await _create_dataset(async_client, "brain-z-left", parent_dataset_id=parent["dataset_id"])

    r = await async_client.post(
        "/api/v2/datasets",
        json={**DS_PAYLOAD, "name": "grandchild", "parent_dataset_id": child["dataset_id"]},
    )
    assert r.status_code == 400
    assert "one level only" in r.json()["detail"]


@pytest.mark.asyncio
async def test_unknown_parent_404(async_client: AsyncClient):
    r = await async_client.post(
        "/api/v2/datasets",
        json={**DS_PAYLOAD, "name": "orphan", "parent_dataset_id": str(uuid.uuid4())},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_children_of_unknown_dataset_404(async_client: AsyncClient):
    r = await async_client.get(f"/api/v2/datasets/{uuid.uuid4()}/children")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_tile_add_rejected_for_parent_dataset(async_client: AsyncClient, test_acquisition, test_dataset):
    await _create_dataset(async_client, "fixture-child", parent_dataset_id=str(test_dataset.dataset_id))

    single = await async_client.post(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles",
        json=_tile_payload(),
    )
    assert single.status_code == 400
    assert "parent datasets hold no tiles" in single.json()["detail"]

    bulk = await async_client.post(
        f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/bulk",
        json=[_tile_payload()],
    )
    assert bulk.status_code == 400
    assert "parent datasets hold no tiles" in bulk.json()["detail"]
