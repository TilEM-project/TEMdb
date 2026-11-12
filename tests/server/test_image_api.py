from datetime import datetime, timezone
from unittest.mock import ANY, Mock

import pytest
from botocore.exceptions import ClientError, NoCredentialsError
from sqlalchemy import and_, null, select

from temdb.models import StorageDefault
from temdb.server.config import config
from temdb.server.sqlmodels import BlockSQLModel, DatasetSQLModel, SectionSQLModel, SpecimenSQLModel, TileSQLModel
from temdb.server.sqlmodels.tile import format_tile_id


@pytest.fixture(params=["acquisition", "section"])
def image_target(request, test_acquisition, test_tile, test_section, test_block, test_dataset):
    if request.param == "acquisition":
        return {
            "model": TileSQLModel,
            "condition": and_(
                TileSQLModel.dataset_id == test_tile.dataset_id,
                TileSQLModel.run_id == test_tile.run_id,
                TileSQLModel.row == test_tile.row,
                TileSQLModel.col == test_tile.col,
                TileSQLModel.retake == test_tile.retake,
            ),
            "field": "image",
            "parent_model": DatasetSQLModel,
            "parent_condition": DatasetSQLModel.dataset_id == test_dataset.dataset_id,
            "path": (
                f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles/"
                f"{format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake)}/image"
            ),
        }
    return {
        "model": SectionSQLModel,
        "condition": SectionSQLModel.id == test_section.id,
        "field": "optical_images",
        "image_name": "post_dropoff_image",
        "parent_model": BlockSQLModel,
        "parent_condition": BlockSQLModel.id == test_block.id,
        "path": f"/api/v2/sections/{test_section.section_id}/images/post_dropoff_image",
    }


def _location(**overrides):
    return {
        "protocol": "s3",
        "server": "http://storage.example.com",
        "bucket": "images",
        "key": "images/test.tif",
        **overrides,
    }


async def _set_image(manager, target, image):
    async with manager.async_session_factory() as session:
        row = await session.scalar(select(target["model"]).where(target["condition"]))
        name = target.get("image_name")
        value = {name: image} if name and image is not None else image
        setattr(row, target["field"], value if value is not None else null())
        await session.commit()


async def _image_state(manager, target):
    async with manager.async_session_factory() as session:
        row = await session.scalar(select(target["model"]).where(target["condition"]))
        value = getattr(row, target["field"])
        name = target.get("image_name")
        return (value or {}).get(name) if name else value, row.updated_at


@pytest.fixture
def image_s3(monkeypatch):
    client = Mock()
    client.generate_presigned_url.return_value = "https://storage.example.com/signed"
    client.head_object.return_value = {"ChecksumSHA256": "checksum"}
    factory = Mock(return_value=client)
    monkeypatch.setattr("boto3.client", factory)

    return client, factory


@pytest.mark.parametrize(
    ("existing", "supplied", "status"),
    [
        (False, False, 400),
        (False, True, 200),
        (True, False, 200),
        (True, True, 200),
    ],
)
async def test_image_upload_location_combinations(
    async_client, test_db_manager, image_target, image_s3, existing, supplied, status
):
    image = _location()
    await _set_image(test_db_manager, image_target, image if existing else None)
    before = await _image_state(test_db_manager, image_target)
    body = {**image, "key": "/" + image["key"], "expiration": 600} if supplied else {}
    body["hash"] = "checksum"

    response = await async_client.post(image_target["path"], json=body)

    assert response.status_code == status, response.text
    after = await _image_state(test_db_manager, image_target)
    if status == 400:
        image_s3[0].generate_presigned_url.assert_not_called()
        assert after == before
    else:
        assert after[0] == image
        assert response.json()["key"] == image["key"]
        assert response.json()["expiration"] == (600 if supplied else 3600)
        if existing:
            assert after == before
        else:
            assert after[1] != before[1]


async def test_image_upload_rejects_changed_location_without_updating_metadata(
    async_client, test_db_manager, image_target, image_s3
):
    await _set_image(test_db_manager, image_target, _location())
    before = await _image_state(test_db_manager, image_target)

    response = await async_client.post(
        image_target["path"], json=_location(key="/other.tif", expiration=600, hash="checksum")
    )

    assert response.status_code == 400, response.text
    assert await _image_state(test_db_manager, image_target) == before
    image_s3[0].generate_presigned_url.assert_not_called()


@pytest.mark.parametrize("slashes", [1, 3])
async def test_image_upload_strips_leading_slashes(async_client, test_db_manager, image_target, image_s3, slashes):
    await _set_image(test_db_manager, image_target, None)
    body = _location(key="/" * slashes + "images/test.tif", expiration=600, hash="checksum")

    response = await async_client.post(image_target["path"], json=body)

    assert response.status_code == 200, response.text
    assert response.json()["key"] == "images/test.tif"
    image_s3[0].generate_presigned_url.assert_called_once_with(
        "put_object", Params={"Bucket": "images", "Key": "images/test.tif", "ChecksumSHA256": "checksum"}, ExpiresIn=600
    )
    assert (await _image_state(test_db_manager, image_target))[0] == _location()


@pytest.mark.parametrize("source", ["parent", "server", "both"])
async def test_image_upload_resolves_parent_and_server_defaults(
    async_client, test_db_manager, image_target, image_s3, monkeypatch, source
):
    await _set_image(test_db_manager, image_target, None)
    parent = StorageDefault(
        protocol="s3",
        server="http://parent.example.com",
        bucket="parent-images",
        expiration=600 if source == "parent" else None,
    )
    server = StorageDefault(protocol="s3", server="http://server.example.com", bucket="server-images", expiration=900)
    async with test_db_manager.async_session_factory() as session:
        row = await session.scalar(select(image_target["parent_model"]).where(image_target["parent_condition"]))
        row.default_storage = parent.model_dump(mode="json", exclude_none=True) if source != "server" else None
        await session.commit()
    monkeypatch.setattr(config, "default_storage", server if source != "parent" else None)

    response = await async_client.post(image_target["path"], json={"key": "images/test.tif", "hash": "checksum"})

    assert response.status_code == 200, response.text
    expected = _location(
        server=parent.server if source != "server" else server.server,
        bucket=parent.bucket if source != "server" else server.bucket,
    )
    assert {key: response.json()[key] for key in expected} == expected
    assert response.json()["expiration"] == (600 if source == "parent" else 900)
    assert (await _image_state(test_db_manager, image_target))[0] == expected
    image_s3[1].assert_called_once_with("s3", endpoint_url=expected["server"], config=ANY)


async def test_image_round_trip_with_default_storage_without_server(
    async_client, test_db_manager, image_target, image_s3, monkeypatch
):
    await _set_image(test_db_manager, image_target, None)
    monkeypatch.setattr(config, "default_storage", StorageDefault(protocol="s3", bucket="images", expiration=900))

    put = await async_client.post(image_target["path"], json={"key": "images/test.tif", "hash": "checksum"})
    get = await async_client.get(image_target["path"])

    assert put.status_code == 200, put.text
    assert get.status_code == 200, get.text
    expected = _location(server=None)
    assert {key: put.json()[key] for key in expected} == expected
    assert {key: get.json()[key] for key in expected} == expected
    assert (await _image_state(test_db_manager, image_target))[0] == expected
    image_s3[1].assert_called_once_with("s3", endpoint_url=None, config=ANY)


@pytest.mark.parametrize("method", ["GET", "DELETE"])
async def test_image_operation_without_metadata_returns_404(
    async_client, test_db_manager, image_target, image_s3, method
):
    await _set_image(test_db_manager, image_target, None)

    response = await async_client.request(method, image_target["path"])

    assert response.status_code == 404, response.text
    image_s3[1].assert_not_called()


@pytest.mark.parametrize("method", ["POST", "GET", "DELETE"])
async def test_image_operation_rejects_gcs(async_client, test_db_manager, image_target, image_s3, method):
    image = _location(protocol="gcs")
    await _set_image(test_db_manager, image_target, None if method == "POST" else image)
    before = await _image_state(test_db_manager, image_target)
    body = {**image, "key": "/" + image["key"], "expiration": 600, "hash": "checksum"} if method == "POST" else None

    response = await async_client.request(method, image_target["path"], json=body)

    assert response.status_code == 501, response.text
    assert await _image_state(test_db_manager, image_target) == before
    image_s3[1].assert_not_called()


@pytest.mark.parametrize("method", ["POST", "GET", "DELETE"])
async def test_image_storage_error_preserves_metadata(
    async_client, test_db_manager, image_target, image_s3, caplog, method
):
    await _set_image(test_db_manager, image_target, None if method == "POST" else _location())
    before = await _image_state(test_db_manager, image_target)
    operation = "delete_object" if method == "DELETE" else "generate_presigned_url"
    getattr(image_s3[0], operation).side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "storage denied"}}, operation
    )
    body = _location(key="/images/test.tif", expiration=600, hash="checksum") if method == "POST" else None

    response = await async_client.request(method, image_target["path"], json=body)

    assert response.status_code == 500, response.text
    assert "storage denied" in caplog.text
    assert await _image_state(test_db_manager, image_target) == before
    if method == "DELETE":
        image_s3[0].delete_object.assert_called_once_with(Bucket="images", Key="images/test.tif")
    else:
        image_s3[0].generate_presigned_url.assert_called_once_with(
            "put_object" if method == "POST" else "get_object",
            Params={
                "Bucket": "images",
                "Key": "images/test.tif",
                **({"ChecksumSHA256": "checksum"} if method == "POST" else {}),
            },
            ExpiresIn=600 if method == "POST" else 3600,
        )


async def test_image_delete_clears_metadata_and_updates_timestamp(
    async_client, test_db_manager, image_target, image_s3
):
    await _set_image(test_db_manager, image_target, _location())
    before = await _image_state(test_db_manager, image_target)

    response = await async_client.delete(image_target["path"])

    assert response.status_code == 204, response.text
    image_s3[0].delete_object.assert_called_once_with(Bucket="images", Key="images/test.tif")
    after = await _image_state(test_db_manager, image_target)
    assert after[0] is None
    assert after[1] != before[1]


async def test_reupload_keeps_prefixed_key(async_client, test_db_manager, image_target, image_s3, monkeypatch):
    await _set_image(test_db_manager, image_target, None)
    monkeypatch.setattr(
        config,
        "default_storage",
        StorageDefault(protocol="s3", server="http://storage.example.com", bucket="images", key_prefix="proj"),
    )
    first = await async_client.post(image_target["path"], json={"key": "images/test.tif", "hash": "checksum"})
    assert first.status_code == 200, first.text

    response = await async_client.post(image_target["path"], json={"hash": "checksum"})

    assert response.status_code == 200, response.text
    assert response.json()["key"] == "proj/images/test.tif"
    assert (await _image_state(test_db_manager, image_target))[0] == _location(key="proj/images/test.tif")


@pytest.mark.parametrize(
    ("key", "stored"),
    [
        ("images/test.tif", "proj/images/test.tif"),
        ("/images/test.tif", "images/test.tif"),
        ("/proj/images/test.tif", "proj/images/test.tif"),
    ],
)
async def test_key_prefix_skips_leading_slash(
    async_client, test_db_manager, image_target, image_s3, monkeypatch, key, stored
):
    """The default key_prefix goes on a key without a leading slash; a key with one is stored as given."""
    await _set_image(test_db_manager, image_target, None)
    monkeypatch.setattr(
        config,
        "default_storage",
        StorageDefault(protocol="s3", server="http://storage.example.com", bucket="images", key_prefix="proj"),
    )

    response = await async_client.post(image_target["path"], json={"key": key, "hash": "checksum"})

    assert response.status_code == 200, response.text
    assert (await _image_state(test_db_manager, image_target))[0] == _location(key=stored)


@pytest.mark.parametrize("method", ["POST", "GET", "DELETE"])
async def test_missing_credentials_is_logged_500(async_client, test_db_manager, image_target, image_s3, caplog, method):
    await _set_image(test_db_manager, image_target, None if method == "POST" else _location())
    before = await _image_state(test_db_manager, image_target)
    operation = "delete_object" if method == "DELETE" else "generate_presigned_url"
    getattr(image_s3[0], operation).side_effect = NoCredentialsError()
    body = _location(key="/images/test.tif", expiration=600, hash="checksum") if method == "POST" else None

    response = await async_client.request(method, image_target["path"], json=body)

    assert response.status_code == 500, response.text
    assert "Unable to locate credentials" in caplog.text
    assert await _image_state(test_db_manager, image_target) == before


async def test_section_upload_uses_own_specimen_block(async_client, test_db_manager, test_section, image_s3):
    async with test_db_manager.async_session_factory() as session:
        block = await session.scalar(select(BlockSQLModel).where(BlockSQLModel.block_id == test_section.block_id))
        block.default_storage = {"protocol": "s3", "server": "http://own.example.com", "bucket": "own"}
        session.add(SpecimenSQLModel(specimen_id="OTHER_SPECIMEN", created_at=datetime.now(timezone.utc)))
        await session.flush()
        session.add(
            BlockSQLModel(
                block_id=test_section.block_id,
                specimen_id="OTHER_SPECIMEN",
                default_storage={"protocol": "s3", "server": "http://other.example.com", "bucket": "other"},
                created_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()

    response = await async_client.post(
        f"/api/v2/sections/{test_section.section_id}/images/post_dropoff_image",
        json={"key": "a.tif", "hash": "checksum"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["bucket"] == "own"


@pytest.mark.parametrize("key", ["", "/", "///"])
async def test_upload_empty_key_is_400(async_client, test_db_manager, image_target, image_s3, monkeypatch, key):
    await _set_image(test_db_manager, image_target, None)
    monkeypatch.setattr(
        config, "default_storage", StorageDefault(protocol="s3", server="http://storage.example.com", bucket="images")
    )

    response = await async_client.post(image_target["path"], json={"key": key, "hash": "checksum"})

    assert response.status_code == 400, response.text
    image_s3[0].generate_presigned_url.assert_not_called()
    assert (await _image_state(test_db_manager, image_target))[0] is None


async def test_complete_run_keeps_tile_image(async_client, test_db_manager, image_s3, test_acquisition, test_tile):
    target = {
        "model": TileSQLModel,
        "condition": and_(TileSQLModel.dataset_id == test_tile.dataset_id, TileSQLModel.run_id == test_tile.run_id),
        "field": "image",
    }
    await _set_image(test_db_manager, target, _location())
    acquisition_path = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}"
    done = await async_client.patch(acquisition_path, json={"status": "complete"})
    assert done.status_code == 200, done.text
    tile_id = format_tile_id(test_acquisition.montage_id, test_tile.row, test_tile.col, test_tile.retake)

    response = await async_client.delete(f"{acquisition_path}/tiles/{tile_id}/image")

    assert response.status_code == 409, response.text
    image_s3[0].delete_object.assert_not_called()
    assert (await _image_state(test_db_manager, target))[0] is not None
