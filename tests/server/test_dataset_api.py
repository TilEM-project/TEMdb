import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from temdb.server.ids import uuid7
from temdb.server.sqlmodels import AcquisitionSQLModel, DatasetSQLModel


@pytest.mark.asyncio
async def test_dataset_row_round_trips(init_db, test_db_manager, test_specimen):
    async with test_db_manager.async_session_factory() as session:
        ds = DatasetSQLModel(
            dataset_id=uuid7(),
            name="mouse42_left_hemi",
            description="left hemisphere volume",
            specimen_id=test_specimen.specimen_id,
            size_class="medium",
            created_at=datetime.now(timezone.utc),
        )
        session.add(ds)
        await session.commit()
        fetched = (
            await session.scalars(select(DatasetSQLModel).where(DatasetSQLModel.name == "mouse42_left_hemi"))
        ).one()
        assert isinstance(fetched.dataset_id, uuid.UUID)
        assert fetched.status == "collecting"
        assert fetched.size_class == "medium"
        assert fetched.tile_hash_modulus is None


@pytest.mark.asyncio
async def test_create_and_get_dataset_by_name(async_client, test_specimen):
    resp = await async_client.post(
        "/api/v2/datasets",
        json={"name": "ds_alpha", "specimen_id": test_specimen.specimen_id, "size_class": "large"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "ds_alpha"
    assert body["status"] == "collecting"
    assert body["size_class"] == "large"
    assert body["tile_hash_modulus"] is None

    got = await async_client.get("/api/v2/datasets/by-name/ds_alpha")
    assert got.status_code == 200
    assert got.json()["dataset_id"] == body["dataset_id"]


@pytest.mark.asyncio
async def test_create_duplicate_name_rejected(async_client):
    await async_client.post("/api/v2/datasets", json={"name": "dup", "size_class": "small"})
    resp = await async_client.post("/api/v2/datasets", json={"name": "dup", "size_class": "small"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_datasets_filters_by_status(async_client):
    await async_client.post("/api/v2/datasets", json={"name": "ds_open", "size_class": "small"})
    created = (await async_client.post("/api/v2/datasets", json={"name": "ds_done", "size_class": "small"})).json()
    await async_client.patch(f"/api/v2/datasets/{created['dataset_id']}", json={"status": "collected"})

    listed = await async_client.get("/api/v2/datasets", params={"status": "collected"})
    names = [d["name"] for d in listed.json()]
    assert names == ["ds_done"]


@pytest.mark.asyncio
async def test_patch_status_sets_collected_at(async_client):
    created = (await async_client.post("/api/v2/datasets", json={"name": "ds_ts", "size_class": "small"})).json()
    patched = await async_client.patch(
        f"/api/v2/datasets/{created['dataset_id']}", json={"status": "collected"}
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "collected"
    assert patched.json()["collected_at"] is not None


@pytest.mark.asyncio
async def test_acquisition_carries_dataset_id(
    init_db, test_db_manager, test_specimen, test_roi, test_acquisition_task, test_dataset, test_microscope
):
    ds_id = test_dataset.dataset_id
    async with test_db_manager.async_session_factory() as session:
        acq = AcquisitionSQLModel(
            acquisition_id="ACQ_DS_001",
            montage_id="M1",
            specimen_id=test_specimen.specimen_id,
            roi_id=test_roi.roi_id,
            acquisition_task_id=test_acquisition_task.task_id,
            microscope_id=test_microscope.microscope_id,
            dataset_id=ds_id,
            hardware_settings={},
            acquisition_settings={},
            start_time=datetime.now(timezone.utc),
        )
        session.add(acq)
        await session.commit()
        fetched = (
            await session.scalars(select(AcquisitionSQLModel).where(AcquisitionSQLModel.acquisition_id == "ACQ_DS_001"))
        ).one()
        assert fetched.dataset_id == ds_id
