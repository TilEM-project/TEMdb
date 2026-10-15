from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from temdb.server.sqlmodels import SectionSQLModel


@pytest.mark.asyncio
async def test_list_substrates(async_client: AsyncClient, test_substrate):
    response = await async_client.get("/api/v2/substrates")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert any(sub["media_id"] == test_substrate.media_id for sub in response_data)


@pytest.mark.asyncio
async def test_list_substrates_filtered_by_layout_type(async_client: AsyncClient, test_substrate, test_layout):
    response = await async_client.get("/api/v2/substrates?media_type=tape")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert all(sub["substrate_layout_id"] == test_layout.layout_id for sub in response_data)
    assert any(sub["media_id"] == test_substrate.media_id for sub in response_data)


@pytest.mark.asyncio
async def test_create_substrate(async_client: AsyncClient, test_layout):
    media_id = f"TEST_SUB_CREATE_{int(datetime.now(timezone.utc).timestamp())}"
    response = await async_client.post(
        "/api/v2/substrates",
        json={
            "media_id": media_id,
            "substrate_layout_id": test_layout.layout_id,
        },
    )
    assert response.status_code == 201
    response_data = response.json()
    assert response_data["media_id"] == media_id
    assert response_data["substrate_layout_id"] == test_layout.layout_id
    assert response_data["aperture_status"] == ["available"] * len(test_layout.apertures)
    assert "created_at" in response_data

    await async_client.delete(f"/api/v2/substrates/{media_id}")


@pytest.mark.asyncio
async def test_create_substrate_duplicate(async_client: AsyncClient, test_substrate):
    response = await async_client.post(
        "/api/v2/substrates",
        json={
            "media_id": test_substrate.media_id,
            "substrate_layout_id": test_substrate.substrate_layout_id,
        },
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_substrate(async_client: AsyncClient, test_substrate):
    response = await async_client.get(f"/api/v2/substrates/{test_substrate.media_id}")
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["media_id"] == test_substrate.media_id
    assert response_data["id"] == test_substrate.id
    assert response_data["substrate_layout_id"] == test_substrate.substrate_layout_id


@pytest.mark.asyncio
async def test_get_substrate_not_found(async_client: AsyncClient):
    response = await async_client.get("/api/v2/substrates/NON_EXISTENT_SUBSTRATE")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_substrate_with_aperture_status(async_client: AsyncClient, test_layout):
    response = await async_client.post(
        "/api/v2/substrates",
        json={
            "media_id": "TEST_SUB_STATUS",
            "substrate_layout_id": test_layout.layout_id,
            "aperture_status": ["used", "damaged", "available"],
        },
    )
    assert response.status_code == 201
    assert response.json()["aperture_status"] == ["used", "damaged", "available"]


@pytest.mark.asyncio
async def test_create_substrate_rejects_a_status_list_of_the_wrong_length(async_client: AsyncClient, test_layout):
    response = await async_client.post(
        "/api/v2/substrates",
        json={"media_id": "TEST_SUB_SHORT", "substrate_layout_id": test_layout.layout_id, "aperture_status": ["used"]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_substrate_with_unknown_layout_is_404(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v2/substrates", json={"media_id": "TEST_SUB_NO_LAYOUT", "substrate_layout_id": "NO_SUCH_LAYOUT"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_substrate_aperture_status(async_client: AsyncClient, test_substrate):
    response = await async_client.patch(
        f"/api/v2/substrates/{test_substrate.media_id}",
        json={"aperture_status": {"0": "damaged", "2": "used"}},
    )
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["aperture_status"] == ["damaged", "available", "used"]
    assert response_data["media_id"] == test_substrate.media_id
    assert response_data["updated_at"] is not None


@pytest.mark.asyncio
async def test_substrate_extra_fields_round_trip(async_client: AsyncClient, test_layout):
    media_id = f"TEST_SUB_EXTRA_{int(datetime.now(timezone.utc).timestamp())}"
    create_response = await async_client.post(
        "/api/v2/substrates",
        json={"media_id": media_id, "substrate_layout_id": test_layout.layout_id, "extra": {"made": "create"}},
    )
    assert create_response.status_code == 201
    assert create_response.json()["extra"] == {"made": "create"}

    patch_response = await async_client.patch(f"/api/v2/substrates/{media_id}", json={"extra": {"patched": True}})
    assert patch_response.status_code == 200
    assert patch_response.json()["extra"] == {"made": "create", "patched": True}

    get_response = await async_client.get(f"/api/v2/substrates/{media_id}")
    assert get_response.json()["extra"] == {"made": "create", "patched": True}


@pytest.mark.asyncio
async def test_update_moves_a_substrate_to_a_layout_with_the_same_aperture_count(
    async_client: AsyncClient, test_substrate, test_layout
):
    layout = await async_client.get(f"/api/v2/layouts/{test_layout.layout_id}")
    copy = {k: layout.json()[k] for k in ("name", "media_type", "apertures", "fiducials")}
    created = await async_client.post("/api/v2/layouts", json=copy | {"layout_id": "TEST_LAYOUT_COPY"})
    assert created.status_code == 201

    response = await async_client.patch(
        f"/api/v2/substrates/{test_substrate.media_id}", json={"substrate_layout_id": "TEST_LAYOUT_COPY"}
    )
    assert response.status_code == 200
    assert response.json()["substrate_layout_id"] == "TEST_LAYOUT_COPY"
    assert response.json()["aperture_status"] == ["available", "available", "available"]


@pytest.mark.asyncio
async def test_update_rejects_a_layout_with_a_different_aperture_count(
    async_client: AsyncClient, test_substrate, test_layout
):
    layout = await async_client.get(f"/api/v2/layouts/{test_layout.layout_id}")
    smaller = {k: layout.json()[k] for k in ("name", "media_type", "fiducials")} | {
        "layout_id": "TEST_LAYOUT_SMALLER",
        "apertures": layout.json()["apertures"][:1],
    }
    assert (await async_client.post("/api/v2/layouts", json=smaller)).status_code == 201

    response = await async_client.patch(
        f"/api/v2/substrates/{test_substrate.media_id}", json={"substrate_layout_id": "TEST_LAYOUT_SMALLER"}
    )
    assert response.status_code == 422
    unknown = await async_client.patch(
        f"/api/v2/substrates/{test_substrate.media_id}", json={"substrate_layout_id": "NO_SUCH_LAYOUT"}
    )
    assert unknown.status_code == 404
    current = await async_client.get(f"/api/v2/substrates/{test_substrate.media_id}")
    assert current.json()["substrate_layout_id"] == test_layout.layout_id


@pytest.mark.asyncio
async def test_delete_substrate(async_client: AsyncClient, test_layout):
    media_id = f"TEST_SUB_DELETE_{int(datetime.now(timezone.utc).timestamp())}"
    create_response = await async_client.post(
        "/api/v2/substrates",
        json={"media_id": media_id, "substrate_layout_id": test_layout.layout_id},
    )
    assert create_response.status_code == 201

    delete_response = await async_client.delete(f"/api/v2/substrates/{media_id}")
    assert delete_response.status_code == 204, delete_response.text

    get_response = await async_client.get(f"/api/v2/substrates/{media_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_substrate_with_sections(async_client: AsyncClient, test_substrate, test_section):
    response = await async_client.delete(f"/api/v2/substrates/{test_substrate.media_id}")
    assert response.status_code == 409
    response_data = response.json()
    assert response_data["error_code"] == "FOREIGN_KEY_VIOLATION"
    assert response_data["context"]["table"] == SectionSQLModel.__tablename__


@pytest.mark.asyncio
async def test_get_substrate_sections(async_client: AsyncClient, test_substrate, test_section):
    response = await async_client.get(f"/api/v2/substrates/{test_substrate.media_id}/sections")
    assert response.status_code == 200
    response_data = response.json()
    assert isinstance(response_data, list)
    assert len(response_data) >= 1
    found_section = next((sec for sec in response_data if sec["section_id"] == test_section.section_id), None)
    assert found_section is not None
    assert found_section["id"] == test_section.id
    assert found_section["media_id"] == test_substrate.media_id


@pytest.mark.asyncio
async def test_update_rejects_an_aperture_the_layout_does_not_have(async_client: AsyncClient, test_substrate):
    response = await async_client.patch(
        f"/api/v2/substrates/{test_substrate.media_id}", json={"aperture_status": {"999": "damaged"}}
    )
    assert response.status_code == 422
    assert (await async_client.get(f"/api/v2/substrates/{test_substrate.media_id}")).json()["aperture_status"] == [
        "available",
        "available",
        "available",
    ]


@pytest.mark.asyncio
async def test_apertures_lists_each_apertures_shape_status_and_sections(
    async_client: AsyncClient, test_substrate, test_layout, test_cutting_session
):
    await async_client.patch(f"/api/v2/substrates/{test_substrate.media_id}", json={"aperture_status": {"1": "used"}})
    for section_number, placement in ((1, {"aperture_index": 1}), (2, {"position": {"x": 20.0, "y": 5.0}})):
        response = await async_client.post(
            "/api/v2/sections",
            json={
                "cutting_session_id": test_cutting_session.cutting_session_id,
                "media_id": test_substrate.media_id,
                "section_number": section_number,
                **placement,
            },
        )
        assert response.status_code == 201

    response = await async_client.get(f"/api/v2/substrates/{test_substrate.media_id}/apertures")
    assert response.status_code == 200
    body = response.json()
    assert body["layout"]["layout_id"] == test_layout.layout_id
    assert body["layout"]["fiducials"][0]["name"] == "origin"
    assert body["layout"]["fiducials"][0]["shape_params"]["width"] == 0.5
    assert [aperture["status"] for aperture in body["apertures"]] == ["available", "used", "available"]
    assert body["apertures"][1]["shape"]["centroid"] == [4.0, 0.0]
    assert body["apertures"][1]["sections"] == [f"{test_substrate.media_id}_S1"]
    assert body["blank_sections"] == [f"{test_substrate.media_id}_S2"]


@pytest.mark.asyncio
async def test_list_substrates_filters_by_layout_and_available_apertures_in_media_id_order(
    async_client: AsyncClient, test_substrate, test_layout
):
    layout = (await async_client.get(f"/api/v2/layouts/{test_layout.layout_id}")).json()
    other = {k: layout[k] for k in ("name", "media_type", "apertures", "fiducials")} | {
        "layout_id": "TEST_LAYOUT_OTHER"
    }
    assert (await async_client.post("/api/v2/layouts", json=other)).status_code == 201
    for media_id, layout_id, statuses in (
        ("SUB003", test_layout.layout_id, ["used", "used", "damaged"]),
        ("SUB002", "TEST_LAYOUT_OTHER", ["used", "available", "used"]),
    ):
        body = {"media_id": media_id, "substrate_layout_id": layout_id, "aperture_status": statuses}
        assert (await async_client.post("/api/v2/substrates", json=body)).status_code == 201

    async def ids(query: str = "limit=100") -> list[str]:
        return [s["media_id"] for s in (await async_client.get(f"/api/v2/substrates?{query}")).json()]

    assert await ids() == ["SUB001", "SUB002", "SUB003"]
    assert await ids("available=true") == ["SUB001", "SUB002"]
    assert await ids("available=false") == ["SUB003"]
    assert await ids(f"layout_id={test_layout.layout_id}") == ["SUB001", "SUB003"]
    assert await ids("layout_id=TEST_LAYOUT_OTHER&available=true") == ["SUB002"]
    assert await ids("skip=1&limit=1") == ["SUB002"]
