from datetime import datetime, timezone

import pytest

from temdb.client.exceptions import TEMdbNotFoundError


async def test_roi_create(client, records):
    section = await records.section()
    created = await client.roi.create(
        created_at=datetime(2026, 1, 1, 3, tzinfo=timezone.utc),
        section_id=section.section_id,
        payload={"vertices": [[0, 0], [10, 0], [10, 10]], "rotation_angle": 0.0},
    )
    assert (await client.roi.get(created.roi_id)).roi_id == "M1.A0000.R001"


async def test_roi_get(client, records):
    roi = await records.roi()
    assert (await client.roi.get(roi.roi_id)).section_id == roi.section_id


async def test_roi_list_by_section(client, records):
    roi = await records.roi()
    assert [r.roi_id for r in await client.roi.list_by_section(roi.section_id)] == [roi.roi_id]


async def test_roi_list_all(client, records):
    roi = await records.roi()
    assert [r.roi_id for r in await client.roi.list_all(section_id=roi.section_id)] == [roi.roi_id]
    assert await client.roi.list_all(section_id="SECTION-NONE") == []


async def test_roi_update(client, records):
    roi = await records.roi()
    updated = await client.roi.update(roi.roi_id, extra={"note": "edge"})
    assert updated.extra["note"] == "edge"


async def test_roi_delete(client, records):
    roi = await records.roi()
    await client.roi.delete(roi.roi_id)
    with pytest.raises(TEMdbNotFoundError):
        await client.roi.get(roi.roi_id)


async def test_roi_get_children(client, records):
    parent = await records.roi()
    child = await client.roi.create(
        created_at=datetime(2026, 1, 1, 3, tzinfo=timezone.utc),
        section_id=parent.section_id,
        parent_created_at=parent.created_at,
        payload={"vertices": [[0, 0], [5, 0], [5, 5]], "rotation_angle": 0.0},
    )
    assert [r.roi_id for r in (await client.roi.get_children(parent.roi_id)).children] == [child.roi_id]


async def test_roi_list_acquisitions(client, records):
    acquisition = await records.acquisition()
    listed = await client.roi.list_acquisitions(acquisition.roi_id)
    assert [a.acquisition_id for a in listed] == ["A1"]
    assert await client.roi.list_acquisitions(acquisition.roi_id, status="complete") == []
    assert await client.roi.list_acquisitions(acquisition.roi_id, qc_state="qc_pass") == []
