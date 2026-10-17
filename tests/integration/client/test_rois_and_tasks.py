import pytest

from temdb.client.exceptions import TEMdbNotFoundError
from temdb.models import (
    AcquisitionTaskCreate,
)


async def test_roi_create(live, seed):
    client = live.client
    section = await seed.section()
    created = await client.roi.create(
        roi_number=2,
        section_id=section.section_id,
        specimen_id="SP1",
        block_id="B1",
        substrate_media_id="M1",
    )
    assert (await client.roi.get(created.roi_id)).roi_number == 2


async def test_roi_get(live, seed):
    client = live.client
    roi = await seed.roi()
    assert (await client.roi.get(roi.roi_id)).section_id == roi.section_id


async def test_roi_list_by_section(live, seed):
    client = live.client
    roi = await seed.roi()
    assert [r.roi_id for r in await client.roi.list_by_section(roi.section_id)] == [roi.roi_id]


async def test_roi_list_all(live, seed):
    client = live.client
    roi = await seed.roi()
    assert [r.roi_id for r in await client.roi.list_all(section_id=roi.section_id)] == [roi.roi_id]
    assert await client.roi.list_all(section_id="SECTION-NONE") == []


async def test_roi_update(live, seed):
    client = live.client
    roi = await seed.roi()
    updated = await client.roi.update(roi.roi_id, extra={"note": "edge"})
    assert updated.extra["note"] == "edge"


async def test_roi_delete(live, seed):
    client = live.client
    roi = await seed.roi()
    await client.roi.delete(roi.roi_id)
    with pytest.raises(TEMdbNotFoundError):
        await client.roi.get(roi.roi_id)


async def test_roi_get_children(live, seed):
    client = live.client
    parent = await seed.roi()
    child = await client.roi.create(
        roi_number=2,
        section_id=parent.section_id,
        specimen_id="SP1",
        block_id="B1",
        substrate_media_id="M1",
        parent_roi_id=parent.roi_id,
    )
    assert [r.roi_id for r in (await client.roi.get_children(parent.roi_id)).children] == [child.roi_id]


async def test_roi_list_acquisitions(live, seed):
    client = live.client
    acquisition = await seed.acquisition()
    listed = await client.roi.list_acquisitions(acquisition.roi_id)
    assert [a.acquisition_id for a in listed] == ["A1"]
    assert await client.roi.list_acquisitions(acquisition.roi_id, status="complete") == []
    assert await client.roi.list_acquisitions(acquisition.roi_id, qc_state="qc_pass") == []


async def test_acquisition_task_create(live, seed):
    client = live.client
    roi = await seed.roi()
    await client.acquisition_task.create(task_id="T-NEW", specimen_id="SP1", block_id="B1", roi_id=roi.roi_id)
    assert (await client.acquisition_task.get("T-NEW")).roi_id == roi.roi_id


async def test_acquisition_task_create_batch(live, seed):
    client = live.client
    roi = await seed.roi()
    created = await client.acquisition_task.create_batch(
        [
            AcquisitionTaskCreate(task_id="T3", specimen_id="SP1", block_id="B1", roi_id=roi.roi_id),
            AcquisitionTaskCreate(task_id="T4", specimen_id="SP1", block_id="B1", roi_id=roi.roi_id),
        ]
    )
    assert {t.task_id for t in created} == {"T3", "T4"}


async def test_acquisition_task_get(live, seed):
    client = live.client
    await seed.task()
    assert (await client.acquisition_task.get("T1")).specimen_id == "SP1"


async def test_acquisition_task_list(live, seed):
    client = live.client
    await seed.task()
    await client.acquisition_task.create(task_id="T9", kind="lens_correction")
    assert {t.task_id for t in await client.acquisition_task.list()} == {"T1", "T9"}
    assert [t.task_id for t in await client.acquisition_task.list(specimen_id="SP1")] == ["T1"]


async def test_acquisition_task_update(live, seed):
    client = live.client
    await seed.task()
    updated = await client.acquisition_task.update("T1", tags=["priority"])
    assert updated.tags == ["priority"]


async def test_acquisition_task_delete(live, seed):
    client = live.client
    await seed.task()
    await client.acquisition_task.delete("T1")
    with pytest.raises(TEMdbNotFoundError):
        await client.acquisition_task.get("T1")


async def test_acquisition_task_supersede(live, seed):
    client = live.client
    roi = await seed.roi()
    await seed.task()
    replacement = await client.acquisition_task.supersede(
        "T1",
        AcquisitionTaskCreate(task_id="T1-B", specimen_id="SP1", block_id="B1", roi_id=roi.roi_id),
    )
    assert replacement.task_id == "T1-B"
    assert (await client.acquisition_task.get("T1")).superseded_by == "T1-B"


async def test_acquisition_task_list_related_acquisitions(live, seed):
    client = live.client
    await seed.acquisition()
    listed = await client.acquisition_task.list_related_acquisitions("T1")
    assert [a.acquisition_id for a in listed] == ["A1"]
