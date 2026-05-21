import httpx

from temdb.models import AcquisitionTaskCreate, AcquisitionTaskUpdate
from temdb.models.task import AcquisitionTaskStatus


def _new_task(task_id: str = "TASK001") -> AcquisitionTaskCreate:
    return AcquisitionTaskCreate(
        task_id=task_id,
        specimen_id="SPEC001",
        block_id="B1",
        roi_id="ROI001",
        task_type="standard_acquisition",
    )


def _task_resp(task_id: str = "TASK001") -> dict:
    return {
        "task_id": task_id,
        "specimen_id": "SPEC001",
        "block_id": "B1",
        "roi_id": "ROI001",
        "task_type": "standard_acquisition",
        "version": 1,
        "status": AcquisitionTaskStatus.PLANNED.value,
    }


async def test_create_posts_required_fields(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_task_resp()))
    await client.acquisition_task.create(_new_task())
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/acquisition-tasks"
    assert req.body["task_id"] == "TASK001"
    assert req.body["task_type"] == "standard_acquisition"


async def test_list_with_status_enum(client, captured):
    await client.acquisition_task.list(status=AcquisitionTaskStatus.PLANNED, limit=10)
    req = captured[-1]
    assert req.method == "GET"
    assert req.path == "/api/v2/acquisition-tasks"
    assert req.params["status"] == "Planned"
    assert req.params["limit"] == "10"


async def test_get_with_version(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_task_resp()))
    await client.acquisition_task.get("TASK001", version=3)
    req = captured[-1]
    assert req.path == "/api/v2/acquisition-tasks/TASK001"
    assert req.params == {"version": "3"}


async def test_get_without_version_omits_params(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_task_resp()))
    await client.acquisition_task.get("TASK001")
    req = captured[-1]
    assert req.path == "/api/v2/acquisition-tasks/TASK001"
    assert req.params == {}


async def test_update_patches(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_task_resp()))
    await client.acquisition_task.update(
        "TASK001", AcquisitionTaskUpdate(tags=["urgent"])
    )
    req = captured[-1]
    assert req.method == "PATCH"
    assert req.path == "/api/v2/acquisition-tasks/TASK001"
    assert req.body == {"tags": ["urgent"]}


async def test_delete(client, captured):
    await client.acquisition_task.delete("TASK001")
    req = captured[-1]
    assert req.method == "DELETE"
    assert req.path == "/api/v2/acquisition-tasks/TASK001"


async def test_list_related_acquisitions(client, captured):
    await client.acquisition_task.list_related_acquisitions("TASK001")
    assert captured[-1].path == "/api/v2/acquisition-tasks/TASK001/acquisitions"


async def test_update_status_posts_enum_value(client, captured, response_queue):
    response_queue.append(httpx.Response(200, json=_task_resp()))
    await client.acquisition_task.update_status(
        "TASK001", AcquisitionTaskStatus.IN_PROGRESS
    )
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/acquisition-tasks/TASK001/status"
    assert req.body == {"status": "In Progress"}


async def test_create_batch_posts_list(client, captured, response_queue):
    response_queue.append(
        httpx.Response(200, json=[_task_resp("T1"), _task_resp("T2")])
    )
    await client.acquisition_task.create_batch([_new_task("T1"), _new_task("T2")])
    req = captured[-1]
    assert req.method == "POST"
    assert req.path == "/api/v2/acquisition-tasks/batch"
    assert isinstance(req.body, list)
    assert len(req.body) == 2
    assert req.body[0]["task_id"] == "T1"
