import io

import pytest
import requests
from minio.error import S3Error

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
async def section_image(client, records, image_location):
    section = await records.section()
    await client.section.put_image("CS1", section.section_id, io.BytesIO(CONTENTS), image_location)
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


async def test_acquisition_put_image(client, tile_image, minio_s3):
    result = await client.acquisition.put_image("A1", tile_image.tile_id, io.BytesIO(b"replacement"))
    assert result.key == "image.tif"
    response = minio_s3["client"].get_object(minio_s3["bucket"], "image.tif")
    try:
        assert response.read() == b"replacement"
    finally:
        response.close()
        response.release_conn()


async def test_acquisition_put_image_urls(client, tile_image):
    result = await client.acquisition.put_image_urls("A1", [tile_image.tile_id], expiration=300)
    assert set(result) == {tile_image.tile_id}
    assert requests.put(result[tile_image.tile_id].url, data=b"bulk upload").status_code == 200


async def test_acquisition_get_image_url(client, tile_image):
    result = await client.acquisition.get_image_url("A1", tile_image.tile_id, expiration=300)
    assert requests.get(result.url).content == CONTENTS


async def test_acquisition_get_image_urls(client, tile_image):
    result = await client.acquisition.get_image_urls("A1", [tile_image.tile_id], expiration=300)
    assert set(result) == {tile_image.tile_id}
    assert requests.get(result[tile_image.tile_id].url).content == CONTENTS


async def test_acquisition_delete_image(client, tile_image, minio_s3):
    await client.acquisition.delete_image("A1", tile_image.tile_id)
    assert (await client.acquisition.get_tile("A1", tile_image.tile_id)).image is None
    assert_object_missing(minio_s3)
    await client.acquisition.delete_tile("A1", tile_image.tile_id)


async def test_acquisition_delete_images(client, tile_image, minio_s3):
    assert await client.acquisition.delete_images("A1", [tile_image.tile_id]) == [tile_image.tile_id]
    assert (await client.acquisition.get_tile("A1", tile_image.tile_id)).image is None
    assert_object_missing(minio_s3)
    await client.acquisition.delete_tile("A1", tile_image.tile_id)


async def test_section_put_image_url(client, records, image_location):
    section = await records.section()
    result = await client.section.put_image_url("CS1", section.section_id, image_location)
    assert requests.put(result.url, data=CONTENTS).status_code == 200
    assert (await client.section.get(section.section_id)).optical_image.key == "image.tif"


async def test_section_put_image(client, section_image):
    result = await client.section.put_image("CS1", section_image.section_id, io.BytesIO(b"replacement"))
    downloaded = await client.section.get_image("CS1", section_image.section_id)
    with downloaded:
        assert downloaded.read() == b"replacement"
    assert result.key == "image.tif"


async def test_section_get_image_url(client, section_image):
    result = await client.section.get_image_url("CS1", section_image.section_id, expiration=300)
    assert requests.get(result.url).content == CONTENTS


async def test_section_get_image(client, section_image):
    image = await client.section.get_image("CS1", section_image.section_id, expiration=300)
    with image:
        assert image.read() == CONTENTS


async def test_section_delete_image(client, section_image, minio_s3):
    await client.section.delete_image("CS1", section_image.section_id)
    assert (await client.section.get(section_image.section_id)).optical_image is None
    assert_object_missing(minio_s3)
