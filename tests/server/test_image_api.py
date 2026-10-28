from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError
from sqlalchemy import and_, null, select

from temdb.models import StorageDefault
from temdb.server.config import config
from temdb.server.sqlmodels import BlockSQLModel, DatasetSQLModel, SectionSQLModel, TileSQLModel
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
        "field": "optical_image",
        "parent_model": BlockSQLModel,
        "parent_condition": BlockSQLModel.id == test_block.id,
        "path": f"/api/v2/sections/{test_section.section_id}/image",
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
        setattr(row, target["field"], image if image is not None else null())
        await session.commit()


async def _image_state(manager, target):
    async with manager.async_session_factory() as session:
        row = await session.scalar(select(target["model"]).where(target["condition"]))
        return getattr(row, target["field"]), row.updated_at


@pytest.fixture
def image_s3(monkeypatch):
    client = Mock()
    client.generate_presigned_url.return_value = "https://storage.example.com/signed"
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
    body = {**image, "key": "/" + image["key"], "expiration": 600} if supplied else None

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

    response = await async_client.post(image_target["path"], json=_location(key="/other.tif", expiration=600))

    assert response.status_code == 400, response.text
    assert await _image_state(test_db_manager, image_target) == before
    image_s3[0].generate_presigned_url.assert_not_called()


@pytest.mark.parametrize("slashes", [1, 3])
async def test_image_upload_strips_leading_slashes(async_client, test_db_manager, image_target, image_s3, slashes):
    await _set_image(test_db_manager, image_target, None)
    body = _location(key="/" * slashes + "images/test.tif", expiration=600)

    response = await async_client.post(image_target["path"], json=body)

    assert response.status_code == 200, response.text
    assert response.json()["key"] == "images/test.tif"
    image_s3[0].generate_presigned_url.assert_called_once_with(
        "put_object", Params={"Bucket": "images", "Key": "images/test.tif"}, ExpiresIn=600
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

    response = await async_client.post(image_target["path"], json={"key": "images/test.tif"})

    assert response.status_code == 200, response.text
    expected = _location(
        server=parent.server if source != "server" else server.server,
        bucket=parent.bucket if source != "server" else server.bucket,
    )
    assert {key: response.json()[key] for key in expected} == expected
    assert response.json()["expiration"] == (600 if source == "parent" else 900)
    assert (await _image_state(test_db_manager, image_target))[0] == expected
    image_s3[1].assert_called_once_with("s3", endpoint_url=expected["server"])


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
    body = {**image, "key": "/" + image["key"], "expiration": 600} if method == "POST" else None

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
    body = _location(key="/images/test.tif", expiration=600) if method == "POST" else None

    response = await async_client.request(method, image_target["path"], json=body)

    assert response.status_code == 500, response.text
    assert "storage denied" in caplog.text
    assert await _image_state(test_db_manager, image_target) == before
    if method == "DELETE":
        image_s3[0].delete_object.assert_called_once_with(Bucket="images", Key="images/test.tif")
    else:
        image_s3[0].generate_presigned_url.assert_called_once_with(
            "put_object" if method == "POST" else "get_object",
            Params={"Bucket": "images", "Key": "images/test.tif"},
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
    first = await async_client.post(image_target["path"], json={"key": "images/test.tif"})
    assert first.status_code == 200, first.text

    response = await async_client.post(image_target["path"])

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

    response = await async_client.post(image_target["path"], json={"key": key})

    assert response.status_code == 200, response.text
    assert (await _image_state(test_db_manager, image_target))[0] == _location(key=stored)
