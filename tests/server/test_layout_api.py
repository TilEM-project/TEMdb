from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from temdb.server.sqlmodels import SubstrateSQLModel


def _layout_payload(layout_id: str) -> dict:
    return {
        "layout_id": layout_id,
        "name": "Test wafer layout",
        "media_type": "wafer",
        "apertures": [
            {
                "shape_type": "circle",
                "shape_params": {"diameter": 1.0},
                "centroid": [1.0, 2.0],
            },
            {
                "shape_type": "polygon",
                "shape_params": {"vertices": [[-7.5, -7.5], [7.5, -7.5], [7.5, 7.5], [-7.5, 7.5]]},
                "centroid": [20.0, 2.0],
            },
        ],
        "fiducials": [
            {
                "shape_type": "circle",
                "shape_params": {"diameter": 0.4},
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
    assert created["apertures"][0]["shape_params"]["diameter"] == 1.0
    assert created["apertures"][1]["shape_type"] == "polygon"
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
async def test_layout_shape_params_that_are_not_an_object_are_rejected(async_client: AsyncClient):
    payload = _layout_payload("LAYOUT_BAD_PARAMS")
    payload["apertures"][0]["shape_params"] = [1.0, 2.0]

    created = await async_client.post("/api/v2/layouts", json=payload)
    updated = await async_client.patch("/api/v2/layouts/LAYOUT_BAD_PARAMS", json={"apertures": payload["apertures"]})

    assert created.status_code == 422
    assert updated.status_code == 422
    [error] = created.json()["context"]["errors"]
    assert error["loc"] == ["body", "apertures", 0, "shape_params"]
    assert error["msg"] == "Input should be a valid dictionary or instance of CircleParams"


@pytest.mark.asyncio
async def test_layout_cannot_be_deleted_when_it_has_substrates(async_client: AsyncClient, test_layout, test_substrate):
    response = await async_client.delete(f"/api/v2/layouts/{test_layout.layout_id}")
    assert response.status_code == 409
    response_data = response.json()
    assert response_data["error_code"] == "FOREIGN_KEY_VIOLATION"
    assert response_data["context"]["table"] == SubstrateSQLModel.__tablename__


@pytest.mark.asyncio
async def test_layout_apertures_cannot_change_once_a_substrate_uses_it(
    async_client: AsyncClient, test_layout, test_substrate
):
    response = await async_client.patch(
        f"/api/v2/layouts/{test_layout.layout_id}",
        json={"apertures": [{"shape_type": "circle", "shape_params": {"diameter": 18.0}, "centroid": [0.0, 0.0]}]},
    )
    assert response.status_code == 409
    renamed = await async_client.patch(f"/api/v2/layouts/{test_layout.layout_id}", json={"name": "Renamed"})
    assert renamed.status_code == 200


@pytest.mark.asyncio
async def test_layout_media_type_and_fiducials_can_change_once_a_substrate_uses_it(
    async_client: AsyncClient, test_layout, test_substrate
):
    fiducials = [
        {
            "name": "origin",
            "shape_type": "circle",
            "shape_params": {"diameter": 0},
            "centroid": [1.0, 2.0],
            "through_shape": False,
        }
    ]
    response = await async_client.patch(
        f"/api/v2/layouts/{test_layout.layout_id}", json={"media_type": "grid_disc", "fiducials": fiducials}
    )
    assert response.status_code == 200
    assert response.json()["media_type"] == "grid_disc"
    assert response.json()["fiducials"][0]["centroid"] == [1.0, 2.0]
