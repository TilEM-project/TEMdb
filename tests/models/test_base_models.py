import pytest
from pydantic import ValidationError

from temdb.models.base import TEMDBRecord


class Example(TEMDBRecord):
    name: str


def test_free_form_fields_go_in_extra():
    model = Example(name="demo", extra={"stain": "2Os_Agar_noUA"})
    assert model.extra == {"stain": "2Os_Agar_noUA"}


def test_unknown_top_level_field_is_rejected():
    with pytest.raises(ValidationError):
        Example(name="demo", stain="2Os_Agar_noUA")


def test_extra_key_that_is_a_field_is_rejected():
    with pytest.raises(ValidationError, match="name"):
        Example(name="demo", extra={"name": "other"})


def nested(depth: int) -> dict:
    value = {"a": 1}
    for _ in range(depth - 1):
        value = {"a": value}
    return value


def test_extra_nested_32_levels_is_accepted():
    assert Example(name="demo", extra=nested(32)).extra == nested(32)


@pytest.mark.parametrize("depth", [33, 5000])
def test_extra_nested_deeper_than_32_levels_is_rejected(depth):
    with pytest.raises(ValidationError, match="32"):
        Example(name="demo", extra=nested(depth))


def test_lists_count_as_nesting_levels():
    with pytest.raises(ValidationError, match="32"):
        Example(name="demo", extra={"a": [nested(32)]})
