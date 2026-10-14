from temdb.server.api.utils import drop_null_keys


def test_drop_null_keys_removes_keys_sent_as_null():
    assert drop_null_keys({"a": 1, "b": None}) == {"a": 1}


def test_drop_null_keys_of_nothing_is_empty():
    assert drop_null_keys(None) == {}
