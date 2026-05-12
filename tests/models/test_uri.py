from unittest.mock import patch

from pydantic import BaseModel, ConfigDict, ValidationError
from pytest import mark, raises
from yaml import safe_load

from temdb.models.utils import uri


def test_uri_create():
    obj_uri = "s3://somebucket/some_obj"
    obj = uri.URI(obj_uri)
    assert obj.uri == obj_uri


@mark.parametrize(
    "obj_uri",
    ["s3://anotherbucket/other_obj", uri.URI("s3://anotherbucket/other_obj")],
)
def test_uri_validate(obj_uri):
    obj = uri.URI.validate(obj_uri)
    assert isinstance(obj, uri.URI)
    assert obj.uri == obj_uri


def test_uri_validate_error():
    with raises(ValueError):
        uri.URI.validate(10)


def test_uri_serialize():
    obj_uri = "s3://somebucket/some_obj"
    obj = uri.URI(obj_uri)
    serialized = uri.URI.serialize(obj)
    assert isinstance(serialized, str)
    assert serialized == obj_uri


@mark.parametrize(
    "obj_uri, transport_params",
    [
        ("s3://somebucket/some_obj", {}),
        (
            "s3://anotherbucket/objectify",
            {
                "client_kwargs": {
                    "aws_access_key_id": "1234",
                    "aws_secret_access_key": "passwordy",
                    "use_ssl": True,
                    "region_name": "us-west-2",
                }
            },
        ),
        (
            "s3u://:@ceph.corp.alleninstitute.org@pail/tile",
            {
                "client_kwargs": {
                    "region_name": "us-east-1",
                    "aws_access_key_id": "5678",
                    "aws_secret_access_key": "don't-tell",
                    "use_ssl": False,
                }
            },
        ),
        (
            "s3u://:@ceph.corp.alleninstitute.org:1234@pail/water",
            {
                "client_kwargs": {
                    "region_name": "us-east-1",
                    "aws_access_key_id": "5678",
                    "aws_secret_access_key": "do-tell",
                    "use_ssl": True,
                }
            },
        ),
    ],
)
def test_uri_open(obj_uri, transport_params):
    uri.URI.data_config = uri._DataConfig(
        data_locations=[
            {
                "transport": "s3",
                "bucket": "anotherbucket",
                "access_key_id": "1234",
                "secret_access_key": "passwordy",
                "region": "us-west-2",
            },
            {
                "transport": "s3",
                "host": "ceph.corp.alleninstitute.org",
                "access_key_id": "5678",
                "secret_access_key": "don't-tell",
                "use_ssl": False,
            },
            {
                "transport": "s3",
                "host": "ceph.corp.alleninstitute.org",
                "access_key_id": "5678",
                "secret_access_key": "do-tell",
                "port": 1234,
            },
        ]
    )
    with patch("temdb.models.utils.uri.open") as open:
        obj = uri.URI(obj_uri)
        file = obj.open("rw")
        open.assert_called_once_with(obj_uri, mode="rw", transport_params=transport_params)
        assert file == open()


@mark.parametrize(
    "obj_uri",
    ["s3://anotherbucket/other_obj", uri.URI("s3://anotherbucket/other_obj")],
)
def test_model_validate(obj_uri):
    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        uri: uri.URI.Type

    obj = Model(uri=obj_uri)
    assert isinstance(obj.uri, uri.URI)
    assert obj.uri == obj_uri


def test_model_validate_error():
    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        uri: uri.URI.Type
        data: str

    with raises(ValidationError) as exc_info:
        Model(uri=5, data=10)

    assert exc_info.value.error_count() == 2


def test_model_serialize():
    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        uri: uri.URI.Type

    obj = Model(uri="/some/path")
    assert obj.model_dump_json() == '{"uri":"/some/path"}'


@mark.parametrize("config_file", ["data_config.yml", "data_config.yaml"])
def test_load_config(config_file, tmp_path):
    yaml_data = """
data_locations:
  - transport: s3
    bucket: pail
    region: us-west-2
  - transport: s3
    bucket: data
    access_key_id: me
    secret_access_key: secret
  - transport: s3
    host: ceph.corp.alleninstitute.org
    port: 4321
    use_ssl: false
    """
    with open(tmp_path / config_file, "w") as f:
        f.write(yaml_data)
    with patch("temdb.models.utils.uri.user_config_path", return_value=tmp_path):
        data = uri._DataConfig.load()
        data_locations = data.data_locations
        for i, location in enumerate(safe_load(yaml_data)["data_locations"]):
            for key, val in location.items():
                assert getattr(data_locations[i], key) == val


def test_load_config_bad(tmp_path):
    with open(tmp_path / "data_config.yaml", "w") as f:
        f.write("This is not parsable")
    with patch("temdb.models.utils.uri.user_config_path", return_value=tmp_path):
        data = uri._DataConfig.load()
        assert data.data_locations == []


def test_load_config_missing(tmp_path):
    with open(tmp_path / "data_config.yaml", "w") as f:
        f.write("This is not parsable")
    with patch("temdb.models.utils.uri.user_config_path", return_value=tmp_path):
        data = uri._DataConfig.load()
        assert data.data_locations == []
