import pytest
from pydantic import ValidationError

from temdb.models import FileObject, FileObjectRequest, FileObjectResponse, StorageDefault
from temdb.models.enums import StorageProtocol


def test_file_object_requires_storage_location():
    image = FileObject(
        protocol=StorageProtocol.S3,
        server="http://s3.example.com",
        bucket="images",
        key="section/image.png",
    )

    assert image.protocol is StorageProtocol.S3
    assert image.key == "section/image.png"


@pytest.mark.parametrize(
    ("location", "error"),
    [
        ({"server": "http://s3.example.com"}, "protocol must also be specified"),
        ({"protocol": "s3"}, "bucket must also be specified"),
        ({"bucket": "images"}, "key must start with a leading slash"),
    ],
)
def test_file_object_request_validates_partial_location(location, error):
    with pytest.raises(ValidationError, match=error):
        FileObjectRequest(key="image.png", **location)


def test_file_object_request_requires_leading_slash_for_explicit_bucket():
    with pytest.raises(ValidationError, match="key must start with a leading slash"):
        FileObjectRequest(protocol="s3", bucket="images", key="section/image.png")


def test_file_object_request_applies_storage_defaults():
    request = FileObjectRequest(key="/section/image.png", expiration=120)
    defaults = StorageDefault(
        protocol="s3",
        server="http://s3.example.com",
        bucket="images",
        key_prefix="project",
        expiration=300,
    )

    request.apply_defaults(defaults)

    assert request.protocol is StorageProtocol.S3
    assert request.server == "http://s3.example.com"
    assert request.bucket == "images"
    assert request.key == "project/section/image.png"
    assert request.expiration == 120


def test_file_object_response_includes_presigned_url_and_expiration():
    response = FileObjectResponse(
        protocol="s3",
        server="http://s3.example.com",
        bucket="images",
        key="section/image.png",
        url="http://s3.example.com/images/section/image.png?signature=example",
        expiration=600,
    )

    assert response.url.endswith("signature=example")
    assert response.expiration == 600


@pytest.mark.parametrize("as_dict", [False, True])
@pytest.mark.parametrize("key", ["image.png", "/image.png"])
def test_request_from_stored_location_normalizes_key_without_mutating_source(as_dict, key):
    stored = FileObject(protocol="s3", server="https://storage.example.com", bucket="images", key=key)
    source = stored.model_dump() if as_dict else stored
    request = FileObjectRequest.from_file_object(source)
    assert request.key == "/image.png"
    assert request.expiration is None
    assert (source["key"] if as_dict else source.key) == key


@pytest.mark.parametrize("expiration", [None, 600])
def test_request_compares_stored_location_without_expiration(expiration):
    stored = FileObject(protocol="s3", server="https://storage.example.com", bucket="images", key="image.png")
    request = FileObjectRequest.from_file_object(stored)
    request.key = stored.key
    request.expiration = expiration
    assert request == stored.model_dump()
    assert stored.model_dump() == request
    assert request != {**stored.model_dump(), "key": "other.png"}
