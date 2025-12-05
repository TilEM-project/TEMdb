from unittest.mock import patch

from pydantic import BaseModel, ConfigDict, ValidationError
from pytest import mark, raises
from temdb.models.utils import uri


def test_uri_create():
    obj_uri = "s3://somebucket/some_obj"
    obj = uri.URIObject(obj_uri)
    assert obj.uri == obj_uri


@mark.parametrize(
    "obj_uri",
    ["s3://anotherbucket/other_obj", uri.URIObject("s3://anotherbucket/other_obj")],
)
def test_uri_validate(obj_uri):
    obj = uri.URIObject.validate(obj_uri)
    assert isinstance(obj, uri.URIObject)
    assert obj.uri == obj_uri


def test_uri_validate_error():
    with raises(ValueError):
        uri.URIObject.validate(10)


def test_uri_serialize():
    obj_uri = "s3://somebucket/some_obj"
    obj = uri.URIObject(obj_uri)
    serialized = uri.URIObject.serialize(obj)
    assert isinstance(serialized, str)
    assert serialized == obj_uri


def test_uri_open():
    obj_uri = "s3://somebucket/some_obj"
    with patch("temdb.models.utils.uri.open") as open:
        obj = uri.URIObject(obj_uri)
        file = obj.open("rw", client="this")
        open.assert_called_once_with(obj_uri, "rw", client="this")
        assert file == open()


@mark.parametrize(
    "obj_uri",
    ["s3://anotherbucket/other_obj", uri.URIObject("s3://anotherbucket/other_obj")],
)
def test_model_validate(obj_uri):
    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        uri: uri.URI

    obj = Model(uri=obj_uri)
    assert isinstance(obj.uri, uri.URIObject)
    assert obj.uri == obj_uri


def test_model_validate_error():
    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        uri: uri.URI
        data: str

    with raises(ValidationError) as exc_info:
        Model(uri=5, data=10)

    assert exc_info.value.error_count() == 2


def test_model_serialize():
    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        uri: uri.URI

    obj = Model(uri="/some/path")
    assert obj.model_dump_json() == '{"uri":"/some/path"}'
