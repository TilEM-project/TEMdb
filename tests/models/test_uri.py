from unittest.mock import patch

from pydantic import BaseModel, ConfigDict, ValidationError
from pytest import mark, raises
from yaml import safe_load

from temdb.models import URI
from temdb.models.utils.uri import _DataConfig, _DataLocationConfig, _S3DataLocation


def test_uri_create():
    obj_uri = "s3://somebucket/some_obj"
    obj = URI(obj_uri)
    assert obj.uri == obj_uri


@mark.parametrize(
    "obj_uri",
    ["s3://anotherbucket/other_obj", URI("s3://anotherbucket/other_obj")],
)
def test_uri_validate(obj_uri):
    obj = URI.validate(obj_uri)
    assert isinstance(obj, URI)
    assert obj.uri == obj_uri


def test_uri_validate_error():
    with raises(ValueError):
        URI.validate(10)


def test_uri_serialize():
    obj_uri = "s3://somebucket/some_obj"
    obj = URI(obj_uri)
    serialized = URI.serialize(obj)
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
    with (
        patch("temdb.models.utils.uri.open") as mock_open,
        patch("temdb.models.utils.uri._DataLocationConfig.get_transport_params", return_value=transport_params),
    ):
        obj = URI(obj_uri)
        file = obj.open("rw")
        mock_open.assert_called_once_with(obj_uri, mode="rw", transport_params=transport_params)
        assert file == mock_open()


@mark.parametrize(
    "obj_uri",
    ["s3://anotherbucket/other_obj", URI("s3://anotherbucket/other_obj")],
)
def test_model_validate(obj_uri):
    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        uri: URI.Type

    obj = Model(uri=obj_uri)
    assert isinstance(obj.uri, URI)
    assert obj.uri == obj_uri


def test_model_validate_error():
    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        uri: URI.Type
        data: str

    with raises(ValidationError) as exc_info:
        Model(uri=5, data=10)

    assert exc_info.value.error_count() == 2


def test_model_serialize():
    class Model(BaseModel):
        model_config = ConfigDict(arbitrary_types_allowed=True)
        uri: URI.Type

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
        data = _DataConfig.load()
        data_locations = data.data_locations
        for i, location in enumerate(safe_load(yaml_data)["data_locations"]):
            for key, val in location.items():
                assert getattr(data_locations[i], key) == val


def test_load_config_bad(tmp_path):
    with open(tmp_path / "data_config.yaml", "w") as f:
        f.write("This is not parsable")
    with patch("temdb.models.utils.uri.user_config_path", return_value=tmp_path):
        data = _DataConfig.load()
        assert data.data_locations == []


def test_load_config_missing(tmp_path):
    with open(tmp_path / "data_config.yaml", "w") as f:
        f.write("This is not parsable")
    with patch("temdb.models.utils.uri.user_config_path", return_value=tmp_path):
        data = _DataConfig.load()
        assert data.data_locations == []


@mark.parametrize(
    "host, port, use_ssl, region, access_key_id, secret_access_key, expected_endpoint",
    [
        (None, 443, True, "us-east-1", None, None, None),
        ("ceph.example.com", 443, True, "us-west-2", "key123", "secret456", "https://ceph.example.com:443"),
        ("ceph.example.com", 9000, False, "us-east-1", "key789", "secret000", "http://ceph.example.com:9000"),
    ],
)
def test_s3_data_location_transport_params(
    host, port, use_ssl, region, access_key_id, secret_access_key, expected_endpoint
):
    with patch("temdb.models.utils.uri.boto3.client") as mock_boto3_client:
        mock_client = mock_boto3_client.return_value

        kwargs = {
            "transport": "s3",
            "port": port,
            "use_ssl": use_ssl,
            "region": region,
        }
        if host is not None:
            kwargs["host"] = host
        if access_key_id is not None:
            kwargs["access_key_id"] = access_key_id
        if secret_access_key is not None:
            kwargs["secret_access_key"] = secret_access_key

        location = _S3DataLocation(**kwargs)

        params = location.transport_params

        mock_boto3_client.assert_called_once_with(
            "s3",
            region_name=region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            use_ssl=use_ssl,
            endpoint_url=expected_endpoint,
        )
        assert "client" in params
        assert params["client"] == mock_client


def test_s3_data_location_match():
    location = _S3DataLocation(
        transport="s3",
        bucket="my-bucket",
        region="us-west-2",
    )

    assert location.match() is True
    assert location.match(bucket_id="my-bucket") is True
    assert location.match(region="us-west-2") is True
    assert location.match(bucket_id="my-bucket", region="us-west-2") is True
    assert location.match(bucket_id="other-bucket") is False
    assert location.match(region="us-east-1") is False
    assert location.match(bucket_id="my-bucket", region="us-east-1") is False


def test_data_location_config_get_transport_params_by_bucket():
    config = _DataLocationConfig(
        data_locations=[
            {
                "transport": "s3",
                "bucket": "bucket1",
                "region": "us-west-2",
                "access_key_id": "key1",
                "secret_access_key": "secret1",
            },
            {
                "transport": "s3",
                "bucket": "bucket2",
                "region": "us-east-1",
                "access_key_id": "key2",
                "secret_access_key": "secret2",
            },
        ]
    )

    with (
        patch.object(config.data_locations[0], "_get_client", return_value="client_bucket1"),
        patch.object(config.data_locations[1], "_get_client", return_value="client_bucket2"),
    ):
        params1 = config.get_transport_params(bucket_id="bucket1")
        assert params1 == {"client": "client_bucket1"}

        params2 = config.get_transport_params(bucket_id="bucket2")
        assert params2 == {"client": "client_bucket2"}

        params_empty = config.get_transport_params(bucket_id="nonexistent")
        assert params_empty == {}


def test_data_location_config_get_transport_params_by_host():
    config = _DataLocationConfig(
        data_locations=[
            {
                "transport": "s3",
                "host": "ceph1.example.com",
                "region": "us-west-2",
                "access_key_id": "key1",
                "secret_access_key": "secret1",
            },
            {
                "transport": "s3",
                "host": "ceph2.example.com",
                "port": 9000,
                "region": "us-east-1",
                "access_key_id": "key2",
                "secret_access_key": "secret2",
            },
        ]
    )

    with (
        patch.object(config.data_locations[0], "_get_client", return_value="client_ceph1"),
        patch.object(config.data_locations[1], "_get_client", return_value="client_ceph2"),
    ):
        params1 = config.get_transport_params(host="ceph1.example.com")
        assert params1 == {"client": "client_ceph1"}

        params2 = config.get_transport_params(host="ceph2.example.com", port=9000)
        assert params2 == {"client": "client_ceph2"}

        params_empty = config.get_transport_params(host="nonexistent.example.com")
        assert params_empty == {}


def test_s3_data_location_client_caching():
    with patch("temdb.models.utils.uri.boto3.client") as mock_boto3_client:
        mock_client = "mock_s3_client"
        mock_boto3_client.return_value = mock_client

        location = _S3DataLocation(
            transport="s3",
            bucket="bucket1",
            region="us-west-2",
            access_key_id="key1",
            secret_access_key="secret1",
        )

        params1 = location.transport_params
        params2 = location.transport_params

        assert params1["client"] == mock_client
        assert params2["client"] == mock_client
        assert params1["client"] is params2["client"]
        assert mock_boto3_client.call_count == 1
