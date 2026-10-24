from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.layout import SubstrateLayoutResource
from temdb.models import SubstrateLayoutUpdate

API = "http://test/api/v2"
NOW = datetime(2026, 10, 8, tzinfo=timezone.utc)


def _layout_resource():
    request = AsyncMock()
    return SubstrateLayoutResource(request, API), request


def _layout_payload(**extra):
    return {
        "layout_id": "LAYOUT001",
        "name": "Test layout",
        "media_type": "wafer",
        "apertures": [],
        "fiducials": [],
        "created_at": NOW.isoformat(),
        **extra,
    }


@pytest.mark.asyncio
async def test_layout_list_filters_and_returns_models():
    resource, request = _layout_resource()
    request.return_value = [_layout_payload()]

    layouts = await resource.list(media_type="wafer", skip=2, limit=5)

    assert request.await_args.args[:2] == ("GET", "layouts")
    assert request.await_args.kwargs["params"] == {"media_type": "wafer", "skip": 2, "limit": 5}
    assert layouts[0].media_type == "wafer"


@pytest.mark.asyncio
async def test_layout_update_patches_and_delete_uses_layout_path():
    resource, request = _layout_resource()
    request.return_value = _layout_payload(name="Updated layout")

    layout = await resource.update("LAYOUT001", SubstrateLayoutUpdate(name="Updated layout"))

    assert request.await_args.args[:2] == ("PATCH", "layouts/LAYOUT001")
    assert request.await_args.kwargs["json"] == {"name": "Updated layout"}
    assert layout.name == "Updated layout"

    await resource.delete("LAYOUT001")
    assert request.await_args.args[:2] == ("DELETE", "layouts/LAYOUT001")
