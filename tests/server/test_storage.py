from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError, InvalidRegionError
from fastapi import HTTPException

from temdb.models import FileObject, FileObjectRequest, StorageProtocol
from temdb.server.storage import StorageClientManager


@pytest.fixture
def s3(monkeypatch):
    client = Mock()
    client.generate_presigned_url.return_value = "https://storage.example.com/signed"
    client.head_object.return_value = {"ChecksumSHA256": "checksum"}
    factory = Mock(return_value=client)
    monkeypatch.setattr("temdb.server.storage.boto3.client", factory)
    return client, factory


@pytest.fixture
def location():
    return FileObject(protocol="s3", server="https://storage.example.com", bucket="images", key="image.tif")


@pytest.mark.parametrize("operation", ["put_url", "get_url", "delete"])
@pytest.mark.parametrize("expiration", [None, 600])
async def test_manager_routes_s3_operations(storage_client_manager, s3, location, operation, expiration):
    client, factory = s3
    if operation == "put_url":
        request = FileObjectRequest.from_file_object(location, "checksum")
        request.expiration = expiration
        storage_client_manager.finalize(request)
        response = await storage_client_manager.put_url(request)
    elif operation == "get_url":
        response = await storage_client_manager.get_url(location, expiration)
    else:
        await storage_client_manager.delete(location)
        client.delete_object.assert_called_once_with(Bucket="images", Key="image.tif")
        return

    factory.assert_called_once_with("s3", endpoint_url=location.server)
    client.generate_presigned_url.assert_called_once_with(
        "put_object" if operation == "put_url" else "get_object",
        Params={
            "Bucket": "images",
            "Key": "image.tif",
            **({"ChecksumSHA256": "checksum"} if operation == "put_url" else {}),
        },
        ExpiresIn=expiration or 3600,
    )
    assert response.url == client.generate_presigned_url.return_value
    assert response.expiration == (expiration or 3600)
    assert response.dump_file_object() == location.model_dump()
    assert response.hash == "checksum"
    if operation == "get_url":
        client.head_object.assert_called_once_with(Bucket="images", Key="image.tif", ChecksumMode="ENABLED")


@pytest.mark.parametrize("operation", ["put_url", "get_url", "delete"])
async def test_s3_errors_become_http_errors(storage_client_manager, s3, location, operation, caplog):
    client, _ = s3
    method = client.delete_object if operation == "delete" else client.generate_presigned_url
    method.side_effect = ClientError({"Error": {"Code": "AccessDenied", "Message": "storage denied"}}, operation)
    argument = FileObjectRequest.from_file_object(location, "checksum") if operation == "put_url" else location

    with pytest.raises(HTTPException) as error:
        await getattr(storage_client_manager, operation)(argument)

    assert error.value.status_code == 500
    assert "storage denied" not in error.value.detail
    assert "storage denied" in caplog.text


def test_s3_creation_failure_is_not_cached(storage_client_manager, s3):
    _, factory = s3
    factory.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "create_client")
    for _ in range(2):
        with pytest.raises(HTTPException) as error:
            storage_client_manager.get_client(StorageProtocol.S3, None)
        assert error.value.status_code == 500
    assert factory.call_count == 2


def test_s3_creation_config_error_is_500(storage_client_manager, s3, caplog):
    _, factory = s3
    factory.side_effect = InvalidRegionError(region_name="bad region!")
    with pytest.raises(HTTPException) as error:
        storage_client_manager.get_client(StorageProtocol.S3, None)
    assert error.value.status_code == 500
    assert "bad region!" in caplog.text


@pytest.mark.parametrize(("protocol", "status"), [("gcs", 501), ("unsupported", 400), (None, 400)])
def test_manager_rejects_unsupported_protocols(storage_client_manager, s3, protocol, status):
    with pytest.raises(HTTPException) as error:
        storage_client_manager.get_client(protocol, None)
    assert error.value.status_code == status
    s3[1].assert_not_called()


def test_manager_reuses_clients_and_evicts_least_recently_used(monkeypatch):
    first, second, third, replacement = [Mock() for _ in range(4)]
    factory = Mock(side_effect=[first, second, third, replacement])
    monkeypatch.setattr("temdb.server.storage.boto3.client", factory)
    manager = StorageClientManager(max_clients=2)
    try:
        cached = manager.get_client("s3", "https://first.example.com")
        manager.get_client("s3", "https://second.example.com")
        assert manager.get_client("s3", "https://first.example.com") is cached
        manager.get_client("s3", "https://third.example.com")
        assert factory.call_count == 3
        second.close.assert_called_once()
        first.close.assert_not_called()
        third.close.assert_not_called()

        manager.get_client("s3", "https://second.example.com")
        assert factory.call_count == 4
        first.close.assert_called_once()
    finally:
        manager.close()

    manager.close()
    for client in (first, second, third, replacement):
        client.close.assert_called_once()


@pytest.mark.parametrize("capacity", [0, -1])
def test_manager_requires_positive_capacity(capacity):
    with pytest.raises(ValueError, match="max_clients"):
        StorageClientManager(max_clients=capacity)


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"protocol": None}, "protocol"),
        ({"bucket": None}, "bucket"),
        ({"key": None}, "key"),
    ],
)
def test_finalize_rejects_missing_location_fields(fields, message):
    request = FileObjectRequest.model_construct(protocol="s3", bucket="images", key="/image.tif")
    for field, value in fields.items():
        setattr(request, field, value)
    with pytest.raises(HTTPException) as error:
        StorageClientManager.finalize(request)
    assert error.value.status_code == 400
    assert message in error.value.detail


@pytest.mark.parametrize("key", ["/image.tif", "///image.tif", "image.tif"])
def test_finalize_normalizes_key_without_changing_expiration(key):
    request = FileObjectRequest.model_construct(protocol="s3", bucket="images", key=key, expiration=600)
    assert StorageClientManager.finalize(request) is request
    assert request.key == "image.tif"
    assert request.expiration == 600


@pytest.mark.parametrize("metadata", [{}, {"ChecksumSHA256": ""}])
async def test_get_url_rejects_missing_checksum(storage_client_manager, s3, location, metadata):
    s3[0].head_object.return_value = metadata
    with pytest.raises(HTTPException, match="SHA 256 hash not in S3 object metadata"):
        await storage_client_manager.get_url(location)


async def test_get_url_handles_checksum_lookup_failure(storage_client_manager, s3, location):
    s3[0].head_object.side_effect = ClientError({"Error": {"Code": "AccessDenied"}}, "HeadObject")
    with pytest.raises(HTTPException, match="Failed to retrieve object hash"):
        await storage_client_manager.get_url(location)


@pytest.mark.parametrize("as_dict", [False, True])
def test_apply_file_object_preserves_checksum_and_explicit_key(location, as_dict):
    source = location.model_dump() if as_dict else location
    request = FileObjectRequest(hash="checksum", expiration=600)
    StorageClientManager.apply_file_object(request, source)
    assert request.hash == "checksum"
    assert request.expiration == 600
    assert request.key == "/image.tif"
    assert request.bucket == "images"
    request.key = "/custom.tif"
    StorageClientManager.apply_file_object(request, source)
    assert request.key == "/custom.tif"
