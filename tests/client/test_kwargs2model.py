import pytest

from temdb.client.resources.base import kwargs2model
from temdb.models.base import TEMDBModel


class _Payload(TEMDBModel):
    value: int
    note: str | None = None


class _Receiver:
    def __init__(self):
        self.calls = []

    @kwargs2model(_Payload)
    async def accept(self, *args) -> dict:
        self.calls.append(args)
        return args


@pytest.mark.parametrize("args", [(), ("from-kwargs",), ("a", "b")])
@pytest.mark.asyncio
async def test_kwargs2model_builds_model_from_kwargs(args):
    recv = _Receiver()
    out = await recv.accept(*args, value=3, note="x")
    assert out == (*args, _Payload(value=3, note="x"))


@pytest.mark.parametrize("args", [(), ("from-kwargs",), ("a", "b")])
@pytest.mark.asyncio
async def test_kwargs2model_passes_model_instance_through(args):
    recv = _Receiver()
    payload = _Payload(value=7)
    out = await recv.accept(*args, payload)
    assert out == (*args, payload)


@pytest.mark.parametrize("args", [(), ("from-kwargs",), ("a", "b")])
@pytest.mark.asyncio
async def test_kwargs2model_rejects_model_plus_kwargs(args):
    recv = _Receiver()
    with pytest.raises(AssertionError):
        await recv.accept(*args, _Payload(value=1), note="conflict")
