import uuid

from temdb.server.ids import uuid7


def test_uuid7_returns_stdlib_uuid_version_7():
    value = uuid7()
    assert isinstance(value, uuid.UUID)
    assert value.version == 7


def test_uuid7_is_time_ordered():
    earlier = uuid7()
    later = uuid7()
    assert later.int >= earlier.int
