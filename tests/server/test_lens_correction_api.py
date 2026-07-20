import uuid

import pytest
from httpx import AsyncClient

MINIMAL_ACQ_PAYLOAD = {
    "hardware_settings": {
        "scope_id": "TEST_SCOPE_001",
        "camera_model": "Test Camera",
        "camera_serial": "12345",
        "camera_bit_depth": 16,
        "media_type": "tape",
    },
    "acquisition_settings": {
        "magnification": 1000,
        "spot_size": 2,
        "exposure_time": 100,
        "tile_size": [4096, 4096],
        "tile_overlap": 0.1,
        "saved_bit_depth": 8,
    },
}


async def _create_microscope(async_client: AsyncClient, label: str) -> dict:
    resp = await async_client.post("/api/v2/microscopes", json={"label": label})
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_lc_create_and_current(async_client: AsyncClient):
    scope = await _create_microscope(async_client, "TEM-01")
    created = (
        await async_client.post(
            "/api/v2/lens-corrections",
            json={
                "microscope_id": scope["microscope_id"],
                "magnification": 20000,
                "started_at": "2026-06-10T00:00:00Z",
                "correction_x_uri": "s3://bucket/lc/x.tiff",
                "correction_y_uri": "s3://bucket/lc/y.tiff",
                "shared_transform": {
                    "className": "mpicbg.trakem2.transform.AffineModel2D",
                    "dataString": "...",
                },
            },
        )
    ).json()
    current = (
        await async_client.get(
            "/api/v2/lens-corrections/current",
            params={"microscope_id": scope["microscope_id"], "magnification": 20000},
        )
    ).json()
    assert current["lc_id"] == created["lc_id"]


@pytest.mark.asyncio
async def test_lc_current_picks_most_recent(async_client: AsyncClient):
    scope = await _create_microscope(async_client, "TEM-02")
    base = {"microscope_id": scope["microscope_id"], "magnification": 4000}
    old = (
        await async_client.post(
            "/api/v2/lens-corrections", json={**base, "started_at": "2026-06-09T00:00:00Z"}
        )
    ).json()
    new = (
        await async_client.post(
            "/api/v2/lens-corrections", json={**base, "started_at": "2026-06-10T00:00:00Z"}
        )
    ).json()
    assert old["lc_id"] != new["lc_id"]
    current = (await async_client.get("/api/v2/lens-corrections/current", params=base)).json()
    assert current["lc_id"] == new["lc_id"]


@pytest.mark.asyncio
async def test_lc_current_404_when_none(async_client: AsyncClient):
    scope = await _create_microscope(async_client, "TEM-03")
    r = await async_client.get(
        "/api/v2/lens-corrections/current",
        params={"microscope_id": scope["microscope_id"], "magnification": 9999},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_microscope_duplicate_label_409(async_client: AsyncClient):
    await _create_microscope(async_client, "TEM-04")
    r = await async_client.post("/api/v2/microscopes", json={"label": "TEM-04"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_microscope_get_by_id_or_label(async_client: AsyncClient):
    scope = await _create_microscope(async_client, "TEM-05")

    by_id = await async_client.get(f"/api/v2/microscopes/{scope['microscope_id']}")
    assert by_id.status_code == 200
    assert by_id.json()["label"] == "TEM-05"

    by_label = await async_client.get("/api/v2/microscopes/TEM-05")
    assert by_label.status_code == 200
    assert by_label.json()["microscope_id"] == scope["microscope_id"]

    missing = await async_client.get("/api/v2/microscopes/NO-SUCH-SCOPE")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_microscope_list_and_patch(async_client: AsyncClient):
    scope = await _create_microscope(async_client, "TEM-06")

    listed = await async_client.get("/api/v2/microscopes")
    assert listed.status_code == 200
    assert scope["microscope_id"] in [m["microscope_id"] for m in listed.json()]

    patched = await async_client.patch(
        f"/api/v2/microscopes/{scope['microscope_id']}",
        json={"location": "Allen Institute, Bay 3"},
    )
    assert patched.status_code == 200
    assert patched.json()["location"] == "Allen Institute, Bay 3"


@pytest.mark.asyncio
async def test_lc_create_unknown_microscope_404(async_client: AsyncClient):
    r = await async_client.post(
        "/api/v2/lens-corrections",
        json={
            "microscope_id": str(uuid.uuid4()),
            "magnification": 4000,
            "started_at": "2026-06-10T00:00:00Z",
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_lc_list_filters_and_get_and_patch(async_client: AsyncClient):
    scope = await _create_microscope(async_client, "TEM-07")
    base = {"microscope_id": scope["microscope_id"], "magnification": 8000}
    first = (
        await async_client.post(
            "/api/v2/lens-corrections", json={**base, "started_at": "2026-06-09T00:00:00Z"}
        )
    ).json()
    second = (
        await async_client.post(
            "/api/v2/lens-corrections", json={**base, "started_at": "2026-06-10T00:00:00Z"}
        )
    ).json()
    await async_client.post(
        "/api/v2/lens-corrections",
        json={
            "microscope_id": scope["microscope_id"],
            "magnification": 2000,
            "started_at": "2026-06-10T00:00:00Z",
        },
    )

    listed = await async_client.get("/api/v2/lens-corrections", params=base)
    assert listed.status_code == 200
    # newest-first by started_at
    assert [lc["lc_id"] for lc in listed.json()] == [second["lc_id"], first["lc_id"]]

    fetched = await async_client.get(f"/api/v2/lens-corrections/{first['lc_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["lc_id"] == first["lc_id"]

    patched = await async_client.patch(
        f"/api/v2/lens-corrections/{first['lc_id']}",
        json={"correction_x_uri": "s3://bucket/lc/backfilled-x.tiff"},
    )
    assert patched.status_code == 200
    assert patched.json()["correction_x_uri"] == "s3://bucket/lc/backfilled-x.tiff"

    missing = await async_client.get(f"/api/v2/lens-corrections/{uuid.uuid4()}")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_lc_create_honors_client_lc_id(async_client: AsyncClient):
    scope = await _create_microscope(async_client, "TEM-08")
    lc_id = str(uuid.uuid4())
    created = await async_client.post(
        "/api/v2/lens-corrections",
        json={
            "lc_id": lc_id,
            "microscope_id": scope["microscope_id"],
            "magnification": 4000,
            "started_at": "2026-06-10T00:00:00Z",
        },
    )
    assert created.status_code == 201
    assert created.json()["lc_id"] == lc_id


@pytest.mark.asyncio
async def test_acquisition_create_carries_lc_id(
    async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope
):
    lc = (
        await async_client.post(
            "/api/v2/lens-corrections",
            json={
                "microscope_id": str(test_microscope.microscope_id),
                "magnification": 20000,
                "started_at": "2026-06-10T00:00:00Z",
            },
        )
    ).json()
    r = await async_client.post(
        "/api/v2/acquisitions",
        json={
            **MINIMAL_ACQ_PAYLOAD,
            "acquisition_id": "ACQ_LC_001",
            "montage_id": "MONTAGE_LC_001",
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "microscope_id": str(test_microscope.microscope_id),
            "kind": "montage",
            "lc_id": lc["lc_id"],
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["lc_id"] == lc["lc_id"]


@pytest.mark.asyncio
async def test_acquisition_create_unknown_lc_id_404(
    async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope
):
    r = await async_client.post(
        "/api/v2/acquisitions",
        json={
            **MINIMAL_ACQ_PAYLOAD,
            "acquisition_id": "ACQ_LC_002",
            "montage_id": "MONTAGE_LC_002",
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "microscope_id": str(test_microscope.microscope_id),
            "kind": "montage",
            "lc_id": str(uuid.uuid4()),
        },
    )
    assert r.status_code == 404
