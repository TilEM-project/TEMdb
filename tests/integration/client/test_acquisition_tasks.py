import pytest

from temdb.client.exceptions import TEMdbNotFoundError
from temdb.models import AcquisitionTaskCreate


async def test_acquisition_task_create(client, records):
    roi = await records.roi()
    await client.acquisition_task.create(task_id="T-NEW", specimen_id="SP1", block_id="B1", roi_id=roi.roi_id)
    assert (await client.acquisition_task.get("T-NEW")).roi_id == roi.roi_id


async def test_acquisition_task_create_batch(client, records):
    roi = await records.roi()
    created = await client.acquisition_task.create_batch(
        [
            AcquisitionTaskCreate(task_id="T3", specimen_id="SP1", block_id="B1", roi_id=roi.roi_id),
            AcquisitionTaskCreate(task_id="T4", specimen_id="SP1", block_id="B1", roi_id=roi.roi_id),
        ]
    )
    assert {t.task_id for t in created} == {"T3", "T4"}


async def test_acquisition_task_get(client, records):
    await records.task()
    assert (await client.acquisition_task.get("T1")).specimen_id == "SP1"


async def test_acquisition_task_list(client, records):
    await records.task()
    await client.acquisition_task.create(task_id="T9", kind="lens_correction")
    assert {t.task_id for t in await client.acquisition_task.list()} == {"T1", "T9"}
    assert [t.task_id for t in await client.acquisition_task.list(specimen_id="SP1")] == ["T1"]


async def test_acquisition_task_update(client, records):
    await records.task()
    updated = await client.acquisition_task.update("T1", tags=["priority"])
    assert updated.tags == ["priority"]


async def test_acquisition_task_delete(client, records):
    await records.task()
    await client.acquisition_task.delete("T1")
    with pytest.raises(TEMdbNotFoundError):
        await client.acquisition_task.get("T1")


async def test_acquisition_task_supersede(client, records):
    roi = await records.roi()
    await records.task()
    replacement = await client.acquisition_task.supersede(
        "T1",
        AcquisitionTaskCreate(task_id="T1-B", specimen_id="SP1", block_id="B1", roi_id=roi.roi_id),
    )
    assert replacement.task_id == "T1-B"
    assert (await client.acquisition_task.get("T1")).superseded_by == "T1-B"


async def test_acquisition_task_list_related_acquisitions(client, records):
    await records.acquisition()
    listed = await client.acquisition_task.list_related_acquisitions("T1")
    assert [a.acquisition_id for a in listed] == ["A1"]
