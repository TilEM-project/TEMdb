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
