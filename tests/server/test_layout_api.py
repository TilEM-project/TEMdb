from datetime import datetime, timezone

import pytest
from httpx import AsyncClient


def _layout_payload(layout_id: str) -> dict:
    return {
        "layout_id": layout_id,
        "name": "Test wafer layout",
        "media_type": "wafer",
        "apertures": {
            "0": {
                "shape_type": "circle",
                "shape_params": {"radius": 0.5},
                "centroid": [1.0, 2.0],
            }
        },
        "fiducials": [
            {
                "shape_type": "circle",
                "shape_params": {"radius": 0.2},
                "centroid": [0.0, 0.0],
                "through_shape": True,
            }
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.mark.asyncio
async def test_layout_create_get_list_update_delete(async_client: AsyncClient):
    layout_id = f"TEST_LAYOUT_{int(datetime.now(timezone.utc).timestamp())}"
    create_response = await async_client.post("/api/v2/layouts", json=_layout_payload(layout_id))
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["layout_id"] == layout_id
    assert created["name"] == "Test wafer layout"
    assert created["media_type"] == "wafer"
    assert created["apertures"]["0"]["shape_params"]["radius"] == 0.5
    assert created["fiducials"][0]["through_shape"] is True

    get_response = await async_client.get(f"/api/v2/layouts/{layout_id}")
    assert get_response.status_code == 200
    assert get_response.json()["layout_id"] == layout_id

    list_response = await async_client.get("/api/v2/layouts?media_type=wafer")
    assert list_response.status_code == 200
    assert any(layout["layout_id"] == layout_id for layout in list_response.json())

    update_response = await async_client.patch(
        f"/api/v2/layouts/{layout_id}",
        json={"name": "Updated layout"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated layout"

    delete_response = await async_client.delete(f"/api/v2/layouts/{layout_id}")
    assert delete_response.status_code == 204
    assert (await async_client.get(f"/api/v2/layouts/{layout_id}")).status_code == 404


@pytest.mark.asyncio
async def test_layout_cannot_be_deleted_when_it_has_substrates(async_client: AsyncClient, test_layout, test_substrate):
    response = await async_client.delete(f"/api/v2/layouts/{test_layout.layout_id}")
    assert response.status_code == 400
    assert "associated substrates" in response.json()["detail"].lower()
