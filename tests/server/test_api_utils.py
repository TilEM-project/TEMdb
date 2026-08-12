from dataclasses import dataclass

from temdb.server.api import utils as api_utils


@dataclass
class _FakeAttr:
    key: str


class _FakeMapper:
    def __init__(self, keys):
        self.column_attrs = [_FakeAttr(key) for key in keys]


class _FakeState:
    def __init__(self, keys):
        self.mapper = _FakeMapper(keys)


class _FakeOrmObject:
    def __init__(self, *, id, name, extra=None):
        self.id = id
        self.name = name
        self.extra = extra


def _fake_sa_inspect(obj, raiseerr=False):
    del raiseerr
    if isinstance(obj, _FakeOrmObject):
        return _FakeState(["id", "name", "extra"])
    return None


async def test_include_extra_merges_orm_extra(monkeypatch):
    monkeypatch.setattr(api_utils, "sa_inspect", _fake_sa_inspect)

    @api_utils.include_extra
    def handler():
        return _FakeOrmObject(id=7, name="specimen", extra={"source": "manual", "id": 999})

    result = await handler()
    assert result == {"source": "manual", "id": 7, "name": "specimen"}


async def test_include_extra_handles_nested_list_tuple_dict(monkeypatch):
    monkeypatch.setattr(api_utils, "sa_inspect", _fake_sa_inspect)

    @api_utils.include_extra
    async def handler():
        return {
            "list": [
                _FakeOrmObject(id=1, name="one", extra={"a": "x"}),
                (
                    _FakeOrmObject(id=2, name="two", extra={"b": "y"}),
                    {"value": _FakeOrmObject(id=3, name="three", extra=None)},
                ),
            ],
        }

    result = await handler()
    assert result == {
        "list": [
            {"a": "x", "id": 1, "name": "one"},
            (
                {"b": "y", "id": 2, "name": "two"},
                {"value": {"id": 3, "name": "three"}},
            ),
        ],
    }


async def test_include_extra_passthrough_for_non_orm_values(monkeypatch):
    monkeypatch.setattr(api_utils, "sa_inspect", _fake_sa_inspect)
    sentinel = object()

    @api_utils.include_extra
    def handler():
        return sentinel

    result = await handler()
    assert result is sentinel
