from temdb.models.base import TEMDBModel


class _ExampleModel(TEMDBModel):
    name: str
    count: int


def test_model_dump_includes_extra_by_default():
    model = _ExampleModel(name="demo", count=1, unknown_key="extra")
    dumped = model.model_dump()
    assert dumped["name"] == "demo"
    assert dumped["count"] == 1
    assert dumped["unknown_key"] == "extra"


def test_model_dump_excludes_extra_when_extra_false():
    model = _ExampleModel(name="demo", count=1, unknown_key="extra")
    dumped = model.model_dump(extra=False)
    assert dumped == {"name": "demo", "count": 1}


def test_model_dump_extra_false_unions_include_sequence_with_model_fields():
    model = _ExampleModel(name="demo", count=1, unknown_key="extra")
    dumped = model.model_dump(extra=False, include=["name"])
    assert dumped == {"name": "demo", "count": 1}


def test_model_dump_extra_false_rejects_invalid_include_type():
    model = _ExampleModel(name="demo", count=1, unknown_key="extra")
    try:
        model.model_dump(extra=False, include={"name": True})
    except ValueError as error:
        assert "include must be a list, set, or tuple" in str(error)
    else:
        raise AssertionError("Expected ValueError for invalid include type")
