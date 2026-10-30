import io

import pytest
import requests
from minio.error import S3Error

from temdb.client.resources.acquisition import DeletedImages
from temdb.models import FileObjectRequest
from tests.integration.client.records import tile_payload

CONTENTS = b"integration image"


@pytest.fixture
def image_location(minio_s3):
    return FileObjectRequest(
        protocol="s3", server=minio_s3["server"], bucket=minio_s3["bucket"], key="/image.tif", expiration=300
    )


@pytest.fixture
async def tile_image(client, records, image_location):
    await records.acquisition()
    tile = await client.acquisition.add_tile("A1", tile_payload(0))
    await client.acquisition.put_image("A1", tile.tile_id, io.BytesIO(CONTENTS), image_location)
    return tile


@pytest.fixture
async def section_image(client, records, image_location, storage_client_manager):
    section = await records.section()
    await client.section.put_image(section.section_id, io.BytesIO(CONTENTS), image_location)
    return section


def assert_object_missing(minio_s3):
    with pytest.raises(S3Error) as error:
        minio_s3["client"].stat_object(minio_s3["bucket"], "image.tif")
    assert error.value.code == "NoSuchKey"


async def test_acquisition_put_image_url(client, records, image_location):
    await records.acquisition()
    tile = await client.acquisition.add_tile("A1", tile_payload(0))
    result = await client.acquisition.put_image_url("A1", tile.tile_id, image_location)
    assert requests.put(result.url, data=CONTENTS).status_code == 200
    assert (await client.acquisition.get_tile("A1", tile.tile_id)).image.key == "image.tif"


async def test_acquisition_put_image(client, tile_image, minio_s3, tmp_path):
    path = tmp_path / "image.tif"
    path.write_bytes(b"replacement")
    with path.open("rb") as image:
        result = await client.acquisition.put_image("A1", tile_image.tile_id, image)
        assert not image.closed
    assert result.key == "image.tif"
    response = minio_s3["client"].get_object(minio_s3["bucket"], "image.tif")
    try:
        assert response.read() == b"replacement"
    finally:
        response.close()
        response.release_conn()


async def test_acquisition_put_image_urls(client, tile_image):
    result = await client.acquisition.put_image_urls("A1", [tile_image.tile_id], expiration=300)
    assert set(result.urls) == {tile_image.tile_id}
    assert requests.put(result.urls[tile_image.tile_id].url, data=b"bulk upload").status_code == 200


async def test_acquisition_all_put_image_urls(client, tile_image):
    result = await client.acquisition.all_put_image_urls("A1", [tile_image.tile_id], expiration=300)
    assert set(result.urls) == {tile_image.tile_id}
    assert result.errors == {}
    assert requests.put(result.urls[tile_image.tile_id].url, data=b"bulk upload").status_code == 200


async def test_acquisition_get_image_url(client, tile_image):
    result = await client.acquisition.get_image_url("A1", tile_image.tile_id, expiration=300)
    assert requests.get(result.url).content == CONTENTS


async def test_acquisition_get_image(client, tile_image):
    image = await client.acquisition.get_image("A1", tile_image.tile_id, expiration=300)
    assert image == CONTENTS


@pytest.mark.parametrize("size", [0, 11, 3 * 1024 * 1024 + 7])
async def test_acquisition_open_image(client, tile_image, size):
    contents = b"x" * size
    async with client.acquisition.open_image("A1", tile_image.tile_id, "wb", size=size) as image:
        await image.write(contents[:5])
        await image.write(contents[5:])
    async with client.acquisition.open_image("A1", tile_image.tile_id, "rb") as image:
        assert await image.read(0) == b""
        assert await image.read(5) == contents[:5]
        assert await image.read() == contents[5:]
        assert await image.read() == b""


async def test_acquisition_get_image_urls(client, tile_image):
    result = await client.acquisition.get_image_urls("A1", [tile_image.tile_id], expiration=300)
    assert set(result.urls) == {tile_image.tile_id}
    assert requests.get(result.urls[tile_image.tile_id].url).content == CONTENTS


async def test_acquisition_all_get_image_urls(client, tile_image):
    result = await client.acquisition.all_get_image_urls("A1", [tile_image.tile_id], expiration=300)
    assert set(result.urls) == {tile_image.tile_id}
    assert result.errors == {}
    assert requests.get(result.urls[tile_image.tile_id].url).content == CONTENTS


async def test_acquisition_delete_image(client, tile_image, minio_s3):
    await client.acquisition.delete_image("A1", tile_image.tile_id)
    assert (await client.acquisition.get_tile("A1", tile_image.tile_id)).image is None
    assert_object_missing(minio_s3)
    await client.acquisition.delete_tile("A1", tile_image.tile_id)


async def test_acquisition_delete_images(client, tile_image, minio_s3):
    result = await client.acquisition.delete_images("A1", [tile_image.tile_id])
    assert result.deleted_images == [tile_image.tile_id]
    assert (await client.acquisition.get_tile("A1", tile_image.tile_id)).image is None
    assert_object_missing(minio_s3)
    await client.acquisition.delete_tile("A1", tile_image.tile_id)


async def test_acquisition_delete_all_images(client, tile_image, minio_s3):
    result = await client.acquisition.delete_all_images("A1")
    assert result == DeletedImages(deleted=[tile_image.tile_id], errors={})
    assert (await client.acquisition.get_tile("A1", tile_image.tile_id)).image is None
    assert_object_missing(minio_s3)
    await client.acquisition.delete_tile("A1", tile_image.tile_id)


async def test_section_put_image_url(client, records, image_location, storage_client_manager):
    section = await records.section()
    result = await client.section.put_image_url(section.section_id, image_location)
    assert requests.put(result.url, data=CONTENTS).status_code == 200
    assert (await client.section.get(section.section_id)).optical_image.key == "image.tif"


async def test_section_put_image(client, section_image):
    result = await client.section.put_image(section_image.section_id, io.BytesIO(b"replacement"))
    assert result.key == "image.tif"
    downloaded = await client.section.get_image(section_image.section_id)
    assert downloaded == b"replacement"


async def test_section_get_image_url(client, section_image):
    result = await client.section.get_image_url(section_image.section_id, expiration=300)
    assert requests.get(result.url).content == CONTENTS


async def test_section_get_image(client, section_image):
    image = await client.section.get_image(section_image.section_id, expiration=300)
    assert image == CONTENTS


async def test_section_open_image(client, section_image):
    async with client.section.open_image(section_image.section_id, "wb", size=11) as image:
        await image.write(b"first")
        await image.write(b"second")
    async with client.section.open_image(section_image.section_id, "rb") as image:
        assert await image.read(5) == b"first"
        assert await image.read() == b"second"


async def test_section_delete_image(client, section_image, minio_s3):
    await client.section.delete_image(section_image.section_id)
    assert (await client.section.get(section_image.section_id)).optical_image is None
    assert_object_missing(minio_s3)
