import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.lens_correction import LensCorrectionResource
from temdb.client.resources.microscope import MicroscopeResource
from temdb.models import (
    LensCorrectionCreate,
    LensCorrectionUpdate,
    MicroscopeCreate,
    MicroscopeUpdate,
)

API = "http://test/api/v2"

SCOPE_ID = str(uuid.uuid4())
LC_ID = str(uuid.uuid4())
NOW = datetime(2026, 6, 10, tzinfo=timezone.utc)


def _lc_resource():
    request = AsyncMock()
    return LensCorrectionResource(request, API), request


def _scope_resource():
    request = AsyncMock()
    return MicroscopeResource(request, API), request


def _scope_payload(**extra) -> dict:
    return {
        "microscope_id": SCOPE_ID,
        "label": "TEM-01",
        "microscope_type": "TEM",
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        **extra,
    }


def _lc_payload(**extra) -> dict:
    return {
        "lc_id": LC_ID,
        "microscope_id": SCOPE_ID,
        "magnification": 20000,
        "started_at": "2026-06-10T00:00:00Z",
        "created_at": NOW.isoformat(),
        "updated_at": NOW.isoformat(),
        **extra,
    }


@pytest.mark.asyncio
async def test_microscope_create_posts():
    res, request = _scope_resource()
    request.return_value = _scope_payload()
    out = await res.create(MicroscopeCreate(label="TEM-01"))
    method, endpoint = request.await_args.args[0], request.await_args.args[1]
    assert (method, endpoint) == ("POST", "microscopes")
    assert request.await_args.kwargs["json"]["label"] == "TEM-01"
    assert out.label == "TEM-01"
    assert str(out.microscope_id) == SCOPE_ID


@pytest.mark.asyncio
async def test_microscope_get_by_id_or_label():
    res, request = _scope_resource()
    request.return_value = _scope_payload()
    await res.get("TEM-01")
    assert request.await_args.args[1] == "microscopes/TEM-01"
    await res.get(SCOPE_ID)
    assert request.await_args.args[1] == f"microscopes/{SCOPE_ID}"


@pytest.mark.asyncio
async def test_microscope_list_returns_models():
    res, request = _scope_resource()
    request.return_value = [_scope_payload(), _scope_payload(label="TEM-02")]
    out = await res.list()
    assert [m.label for m in out] == ["TEM-01", "TEM-02"]
    assert request.await_args.args[1] == "microscopes"


@pytest.mark.asyncio
async def test_microscope_update_patches():
    res, request = _scope_resource()
    request.return_value = _scope_payload(location="Bay 3")
    out = await res.update(SCOPE_ID, MicroscopeUpdate(location="Bay 3"))
    assert request.await_args.args[0] == "PATCH"
    assert request.await_args.args[1] == f"microscopes/{SCOPE_ID}"
    assert request.await_args.kwargs["json"] == {"location": "Bay 3"}
    assert out.location == "Bay 3"


@pytest.mark.asyncio
async def test_lc_create_posts():
    res, request = _lc_resource()
    request.return_value = _lc_payload(correction_x_uri="s3://bucket/lc/x.tiff")
    out = await res.create(
        LensCorrectionCreate(
            microscope_id=SCOPE_ID,
            magnification=20000,
            started_at=NOW,
            correction_x_uri="s3://bucket/lc/x.tiff",
        )
    )
    method, endpoint = request.await_args.args[0], request.await_args.args[1]
    assert (method, endpoint) == ("POST", "lens-corrections")
    sent = request.await_args.kwargs["json"]
    assert sent["microscope_id"] == SCOPE_ID
    assert sent["magnification"] == 20000
    assert "lc_id" not in sent  # exclude_unset: server assigns
    assert str(out.lc_id) == LC_ID


@pytest.mark.asyncio
async def test_lc_create_accepts_kwargs_via_decorator():
    res, request = _lc_resource()
    request.return_value = _lc_payload()
    out = await res.create(
        microscope_id=SCOPE_ID,
        magnification=20000,
        started_at=NOW,
    )
    assert request.await_args.kwargs["json"]["microscope_id"] == SCOPE_ID
    assert out.magnification == 20000


@pytest.mark.asyncio
async def test_lc_create_rejects_model_plus_kwargs():
    res, _ = _lc_resource()
    with pytest.raises(AssertionError):
        await res.create(
            LensCorrectionCreate(microscope_id=SCOPE_ID, magnification=20000, started_at=NOW),
            correction_x_uri="s3://bucket/lc/x.tiff",
        )


@pytest.mark.asyncio
async def test_lc_get():
    res, request = _lc_resource()
    request.return_value = _lc_payload()
    out = await res.get(LC_ID)
    assert request.await_args.args[1] == f"lens-corrections/{LC_ID}"
    assert str(out.lc_id) == LC_ID


@pytest.mark.asyncio
async def test_lc_get_current_uses_current_path():
    res, request = _lc_resource()
    request.return_value = _lc_payload()
    out = await res.get_current(SCOPE_ID, 20000)
    assert request.await_args.args[1] == "lens-corrections/current"
    assert request.await_args.kwargs["params"] == {"microscope_id": SCOPE_ID, "magnification": 20000}
    assert str(out.lc_id) == LC_ID


@pytest.mark.asyncio
async def test_lc_list_filters_and_returns_models():
    res, request = _lc_resource()
    request.return_value = [_lc_payload(), _lc_payload(lc_id=str(uuid.uuid4()))]
    out = await res.list(microscope_id=SCOPE_ID, magnification=20000)
    assert request.await_args.args[1] == "lens-corrections"
    assert request.await_args.kwargs["params"] == {
        "microscope_id": SCOPE_ID,
        "magnification": 20000,
        "skip": 0,
        "limit": 50,
    }
    assert len(out) == 2


@pytest.mark.asyncio
async def test_lc_update_patches_artifacts():
    res, request = _lc_resource()
    request.return_value = _lc_payload(correction_y_uri="s3://bucket/lc/y.tiff")
    out = await res.update(LC_ID, LensCorrectionUpdate(correction_y_uri="s3://bucket/lc/y.tiff"))
    assert request.await_args.args[0] == "PATCH"
    assert request.await_args.args[1] == f"lens-corrections/{LC_ID}"
    assert request.await_args.kwargs["json"] == {"correction_y_uri": "s3://bucket/lc/y.tiff"}
    assert out.correction_y_uri == "s3://bucket/lc/y.tiff"


@pytest.mark.asyncio
async def test_lc_update_accepts_kwargs_via_decorator():
    res, request = _lc_resource()
    request.return_value = _lc_payload(correction_y_uri="s3://bucket/lc/y.tiff")
    out = await res.update(LC_ID, correction_y_uri="s3://bucket/lc/y.tiff")
    assert request.await_args.kwargs["json"] == {"correction_y_uri": "s3://bucket/lc/y.tiff"}
    assert out.correction_y_uri == "s3://bucket/lc/y.tiff"


@pytest.mark.asyncio
async def test_client_attaches_resources(client):
    assert isinstance(client.microscope, MicroscopeResource)
    assert isinstance(client.lens_correction, LensCorrectionResource)
