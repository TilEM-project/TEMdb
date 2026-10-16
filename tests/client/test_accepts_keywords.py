from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from temdb.client.resources.acquisition import AcquisitionResource
from temdb.client.resources.base import accepts_keywords
from temdb.client.resources.block import BlockResource
from temdb.client.resources.specimen import SpecimenResource
from temdb.models import SpecimenCreate
from temdb.models.base import TEMDBModel


class Payload(TEMDBModel):
    value: int
    note: str | None = None


class Receiver:
    @accepts_keywords(Payload)
    async def accept(self, *args) -> tuple:
        return args


class Updater:
    @accepts_keywords(Payload)
    async def update(self, parent_id: str, child_id: str, payload: Payload) -> tuple:
        return parent_id, child_id, payload


@pytest.mark.parametrize("args", [(), ("from-kwargs",), ("a", "b")])
@pytest.mark.asyncio
async def test_builds_model_from_keywords(args):
    out = await Receiver().accept(*args, value=3, note="x")
    assert out == (*args, Payload(value=3, note="x"))


@pytest.mark.parametrize("args", [(), ("from-kwargs",), ("a", "b")])
@pytest.mark.asyncio
async def test_passes_model_instance_through(args):
    payload = Payload(value=7)
    out = await Receiver().accept(*args, payload)
    assert out == (*args, payload)


@pytest.mark.asyncio
async def test_model_passed_by_parameter_name_is_sent_as_given():
    payload = Payload(value=7)
    out = await Receiver().accept("a", payload_data=payload)
    assert out == ("a", payload)


@pytest.mark.parametrize(
    "call",
    [
        lambda updater: updater.update(parent_id="P", child_id="C", value=1),
        lambda updater: updater.update("P", child_id="C", value=1),
        lambda updater: updater.update(parent_id="P", child_id="C", payload=Payload(value=1)),
        lambda updater: updater.update("P", "C", payload=Payload(value=1)),
    ],
)
@pytest.mark.asyncio
async def test_ids_passed_by_keyword_reach_their_parameters(call):
    assert await call(Updater()) == ("P", "C", Payload(value=1))


@pytest.mark.asyncio
async def test_update_with_keyword_ids_patches_that_block():
    request = AsyncMock(
        return_value={"id": 1, "specimen_id": "S", "block_id": "B", "created_at": "2026-10-07T00:00:00Z"}
    )
    blocks = BlockResource(request, "http://test/api/v2")
    await blocks.update(specimen_id="S", block_id="B", description="x")
    assert request.await_args.args == ("PATCH", "blocks/specimens/S/blocks/B")
    assert request.await_args.kwargs["json"] == {"description": "x"}


@pytest.mark.parametrize("args", [(), ("from-kwargs",), ("a", "b")])
@pytest.mark.asyncio
async def test_model_plus_keywords_is_a_type_error(args):
    with pytest.raises(TypeError):
        await Receiver().accept(*args, Payload(value=1), note="conflict")


@pytest.mark.asyncio
async def test_update_sends_only_the_keywords_given():
    request = AsyncMock(return_value={"id": 1, "specimen_id": "S1", "created_at": "2026-10-07T00:00:00Z"})
    specimens = SpecimenResource(request, "http://test/api/v2")
    await specimens.update("S1", description="new")
    assert request.await_args.kwargs["json"] == {"description": "new"}


@pytest.mark.asyncio
async def test_create_by_keywords_sends_the_same_body_as_by_model():
    request = AsyncMock(return_value={"id": 1, "specimen_id": "S1", "created_at": "2026-10-07T00:00:00Z"})
    specimens = SpecimenResource(request, "http://test/api/v2")
    await specimens.create(specimen_id="S1", description="d")
    by_keyword = request.await_args.kwargs["json"]
    await specimens.create(SpecimenCreate(specimen_id="S1", description="d"))
    assert by_keyword == request.await_args.kwargs["json"]


@pytest.mark.asyncio
async def test_unknown_keyword_fails_before_any_request():
    request = AsyncMock()
    acquisitions = AcquisitionResource(request, "http://test/api/v2")
    with pytest.raises(ValidationError):
        await acquisitions.update("A1", tile_cout=3)
    with pytest.raises(ValidationError):
        await acquisitions.update_tile("A1", "T1", focus_scor=0.5)
    request.assert_not_awaited()


def test_docstring_says_the_method_takes_keywords():
    assert SpecimenResource.create.__doc__ == (
        "Create a new specimen.\n\nTakes a SpecimenCreate or its fields as keywords, not both."
    )
