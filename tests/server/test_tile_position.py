import pytest
from httpx import AsyncClient
from sqlalchemy import inspect

from temdb.server.sqlmodels import TileSQLModel


def _tile(row: int, col: int, *, retake: int | None = None, focus_score: float = 0.8) -> dict:
    tile = {
        "raster_index": row * 100 + col,
        "stage_position": {"x": col * 1000.0, "y": row * 1000.0},
        "raster_position": {"row": row, "col": col},
        "focus_score": focus_score,
        "min_value": 10,
        "max_value": 240,
        "mean_value": 100,
        "std_value": 20,
        "image": {
            "protocol": "s3",
            "server": "http://localhost:9000",
            "bucket": "images",
            "key": f"/raw/r{row}_c{col}_{retake}.tif",
        },
    }
    if retake is not None:
        tile["retake"] = retake
    return tile


def _tiles_url(acquisition) -> str:
    return f"/api/v2/acquisitions/{acquisition.acquisition_id}/tiles"


def test_tile_primary_key_is_position_and_retake():
    columns = {column.key for column in inspect(TileSQLModel).column_attrs}
    primary_key = [column.name for column in inspect(TileSQLModel).mapper.primary_key]

    assert primary_key == ["dataset_id", "run_id", "row", "col", "retake"]
    assert columns.isdisjoint({"tile_id", "extra", "montage_row", "montage_col"})


@pytest.mark.asyncio
async def test_tile_id_is_montage_and_position(async_client: AsyncClient, test_acquisition):
    created = await async_client.post(_tiles_url(test_acquisition), json=_tile(3, 12))

    assert created.status_code == 201, created.text
    assert created.json()["tile_id"] == "TEST_MONTAGE_001_r003_c012"
    assert created.json()["retake"] == 0
    read = await async_client.get(f"{_tiles_url(test_acquisition)}/TEST_MONTAGE_001_r003_c012")
    assert read.status_code == 200
    assert read.json()["raster_position"] == {"row": 3, "col": 12}


@pytest.mark.asyncio
async def test_retake_is_stored_beside_first_capture(async_client: AsyncClient, test_acquisition):
    await async_client.post(_tiles_url(test_acquisition), json=_tile(0, 1))
    retake = await async_client.post(_tiles_url(test_acquisition), json=_tile(0, 1, retake=1, focus_score=0.9))

    assert retake.status_code == 201, retake.text
    assert retake.json()["tile_id"] == "TEST_MONTAGE_001_r000_c001_a1"
    first = await async_client.get(f"{_tiles_url(test_acquisition)}/TEST_MONTAGE_001_r000_c001")
    second = await async_client.get(f"{_tiles_url(test_acquisition)}/TEST_MONTAGE_001_r000_c001_a1")
    assert (first.json()["focus_score"], second.json()["focus_score"]) == (pytest.approx(0.8), pytest.approx(0.9))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tile_id",
    [
        "TEST_MONTAGE_001_r000_c009",
        "OTHER_MONTAGE_r000_c001",
        "TEST_MONTAGE_001_r0_c1",
        "TEST_MONTAGE_001_r000_c001_a0",
        "not-a-tile",
    ],
)
@pytest.mark.parametrize("method, body", [("GET", None), ("PATCH", {"focus_score": 0.5}), ("DELETE", None)])
async def test_unknown_tile_id_is_404(async_client: AsyncClient, test_acquisition, tile_id: str, method: str, body):
    await async_client.post(_tiles_url(test_acquisition), json=_tile(0, 1))

    response = await async_client.request(method, f"{_tiles_url(test_acquisition)}/{tile_id}", json=body)

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_tile_list_pages_in_position_order(async_client: AsyncClient, test_acquisition):
    tiles = [_tile(1, 0), _tile(0, 1, retake=1), _tile(0, 0), _tile(0, 1)]
    await async_client.post(f"{_tiles_url(test_acquisition)}/bulk", json=tiles)

    names, cursor = [], None
    while True:
        params = {"limit": 3} | ({"cursor": cursor} if cursor else {})
        page = (await async_client.get(_tiles_url(test_acquisition), params=params)).json()
        names += [tile["tile_id"] for tile in page["tiles"]]
        cursor = page["metadata"]["next_cursor"]
        if not page["metadata"]["has_more"]:
            break

    assert names == [
        "TEST_MONTAGE_001_r000_c000",
        "TEST_MONTAGE_001_r000_c001",
        "TEST_MONTAGE_001_r000_c001_a1",
        "TEST_MONTAGE_001_r001_c000",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("cursor", ["7", "0,1", "a,b,c", "0,1,2,3"])
async def test_malformed_tile_cursor_is_422(async_client: AsyncClient, test_acquisition, cursor: str):
    response = await async_client.get(_tiles_url(test_acquisition), params={"cursor": cursor})

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_bulk_resend_of_identical_tiles_is_skipped(async_client: AsyncClient, test_acquisition):
    tiles = [_tile(0, 0), _tile(0, 1)]
    await async_client.post(f"{_tiles_url(test_acquisition)}/bulk", json=tiles)

    resent = await async_client.post(f"{_tiles_url(test_acquisition)}/bulk", json=tiles)

    assert resent.status_code == 200, resent.text
    assert (resent.json()["inserted"], resent.json()["skipped_existing"]) == (0, 2)


@pytest.mark.asyncio
async def test_bulk_conflict_is_409_and_stores_nothing(async_client: AsyncClient, test_acquisition):
    await async_client.post(_tiles_url(test_acquisition), json=_tile(0, 0))

    response = await async_client.post(
        f"{_tiles_url(test_acquisition)}/bulk", json=[_tile(0, 0, focus_score=0.1), _tile(0, 1)]
    )

    assert response.status_code == 409, response.text
    assert "TEST_MONTAGE_001_r000_c000" in response.json()["detail"]
    stored = (await async_client.get(_tiles_url(test_acquisition))).json()["tiles"]
    assert [(tile["tile_id"], tile["focus_score"]) for tile in stored] == [
        ("TEST_MONTAGE_001_r000_c000", pytest.approx(0.8))
    ]


@pytest.mark.asyncio
async def test_duplicate_position_in_bulk_request_is_422(async_client: AsyncClient, test_acquisition):
    response = await async_client.post(f"{_tiles_url(test_acquisition)}/bulk", json=[_tile(0, 0), _tile(0, 0)])

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_bulk_update_and_delete_by_tile_id(async_client: AsyncClient, test_acquisition):
    await async_client.post(f"{_tiles_url(test_acquisition)}/bulk", json=[_tile(0, 0) | {"image": None}, _tile(0, 1)])

    patched = await async_client.patch(
        f"{_tiles_url(test_acquisition)}/bulk", json={"TEST_MONTAGE_001_r000_c001": {"focus_score": 0.1}}
    )
    deleted = await async_client.request(
        "DELETE",
        f"{_tiles_url(test_acquisition)}/bulk",
        json=["TEST_MONTAGE_001_r000_c000", "TEST_MONTAGE_001_r009_c009"],
    )

    assert patched.status_code == 200, patched.text
    assert [(tile["tile_id"], tile["focus_score"]) for tile in patched.json()] == [
        ("TEST_MONTAGE_001_r000_c001", pytest.approx(0.1))
    ]
    assert deleted.json() == {"requested": 2, "deleted": 1, "not_found": ["TEST_MONTAGE_001_r009_c009"]}


@pytest.mark.asyncio
async def test_tile_count_counts_positions_not_retakes(async_client: AsyncClient, test_acquisition):
    await async_client.post(
        f"{_tiles_url(test_acquisition)}/bulk", json=[_tile(0, 0), _tile(0, 0, retake=1), _tile(0, 1)]
    )

    count = await async_client.get(f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tile-count")

    assert count.json() == {"tile_count": 2}


@pytest.mark.asyncio
async def test_focus_scores_use_newest_retake(async_client: AsyncClient, test_acquisition):
    await async_client.post(
        f"{_tiles_url(test_acquisition)}/bulk",
        json=[_tile(0, 0, focus_score=0.2), _tile(0, 0, retake=1, focus_score=0.9)],
    )

    scores = (await async_client.get(f"/api/v2/qc/{test_acquisition.acquisition_id}/focus-scores")).json()

    assert [(tile["tile_id"], tile["focus_score"]) for tile in scores["focus_scores"]] == [
        ("TEST_MONTAGE_001_r000_c000_a1", pytest.approx(0.9))
    ]


@pytest.mark.asyncio
async def test_tile_update_rejects_new_position(async_client: AsyncClient, test_acquisition):
    await async_client.post(_tiles_url(test_acquisition), json=_tile(0, 0))

    response = await async_client.patch(
        f"{_tiles_url(test_acquisition)}/TEST_MONTAGE_001_r000_c000", json={"raster_position": {"row": 5, "col": 5}}
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_stage_position_z_is_optional(async_client: AsyncClient, test_acquisition):
    with_z = _tile(0, 0)
    with_z["stage_position"]["z"] = -1250.5
    await async_client.post(f"{_tiles_url(test_acquisition)}/bulk", json=[with_z, _tile(0, 1)])

    stored = (await async_client.get(_tiles_url(test_acquisition))).json()["tiles"]

    assert [tile["stage_position"] for tile in stored] == [
        {"x": 0.0, "y": 0.0, "z": -1250.5},
        {"x": 1000.0, "y": 0.0, "z": None},
    ]


@pytest.mark.asyncio
async def test_tiles_have_no_extra(async_client: AsyncClient, test_acquisition):
    response = await async_client.post(_tiles_url(test_acquisition), json=_tile(0, 0) | {"extra": {"a": 1}})

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_inverted_bbox_is_422_without_dataset(
    async_client: AsyncClient, test_roi, test_acquisition_task, test_microscope
):
    created = await async_client.post(
        "/api/v2/acquisitions",
        json={
            "acquisition_id": "ACQ_NO_DATASET",
            "montage_id": "M_NO_DS",
            "roi_id": test_roi.roi_id,
            "acquisition_task_id": test_acquisition_task.task_id,
            "microscope_id": test_microscope.microscope_id,
            "hardware_settings": {
                "camera_model": "C",
                "camera_serial": "X",
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
            "tilt_angle_deg": 0.0,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["dataset_id"] is None

    response = await async_client.get("/api/v2/acquisitions/ACQ_NO_DATASET/tiles", params={"x_min": 100, "x_max": 10})

    assert response.status_code == 422, response.text
