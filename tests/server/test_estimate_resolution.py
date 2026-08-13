import pytest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "estimate,expected",
    [
        (50_000_000, "small"),
        (500_000_000, "medium"),
        (5_000_000_000, "large"),
        (20_000_000_000, "xlarge"),
    ],
)
async def test_create_resolves_size_class_from_estimate(async_client, estimate, expected):
    resp = await async_client.post(
        "/api/v2/datasets", json={"name": f"ds_{estimate}", "estimated_tile_count": estimate}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["size_class"] == expected
    assert body["estimated_tile_count"] == estimate


@pytest.mark.asyncio
async def test_explicit_size_class_overrides_estimate(async_client):
    resp = await async_client.post(
        "/api/v2/datasets",
        json={"name": "ds_override", "size_class": "small", "estimated_tile_count": 20_000_000_000},
    )
    assert resp.status_code == 201
    assert resp.json()["size_class"] == "small"


@pytest.mark.asyncio
async def test_create_without_size_or_estimate_is_400(async_client):
    resp = await async_client.post("/api/v2/datasets", json={"name": "ds_nosize"})
    assert resp.status_code == 400
