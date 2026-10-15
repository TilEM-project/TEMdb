from unittest.mock import AsyncMock

import pytest

from temdb.client.resources.substrate import SubstrateResource


@pytest.mark.asyncio
async def test_get_apertures_returns_each_apertures_status_and_sections():
    request = AsyncMock(
        return_value={
            "media_id": "001105",
            "layout": {"layout_id": "grid_disc-56-1a2b3c4d", "media_type": "grid_disc"},
            "apertures": [
                {
                    "index": 0,
                    "shape": {"shape_type": "circle", "shape_params": {"diameter": 9.0}, "centroid": [0.0, 0.0]},
                    "status": "used",
                    "sections": ["001105_S1"],
                }
            ],
            "blank_sections": [],
        }
    )
    substrates = SubstrateResource(request, "http://test/api/v2")
    apertures = await substrates.get_apertures("001105")
    assert request.await_args.args[:2] == ("GET", "substrates/001105/apertures")
    assert apertures.apertures[0].status == "used"
    assert apertures.apertures[0].sections == ["001105_S1"]


@pytest.mark.asyncio
async def test_update_sends_only_the_apertures_changed():
    request = AsyncMock(
        return_value={"id": 1, "media_id": "001105", "substrate_layout_id": "L", "aperture_status": ["damaged"]}
    )
    substrates = SubstrateResource(request, "http://test/api/v2")
    await substrates.update("001105", aperture_status={0: "damaged"})
    assert request.await_args.kwargs["json"] == {"aperture_status": {0: "damaged"}}
