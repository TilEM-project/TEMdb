# Working with Images

TEMdb stores the path to an image. The client asks TEMdb for a signed URL and moves the bytes
directly to or from storage. `TEMdbClient` is asynchronous, so call it from a coroutine.

## Section Images

A section holds up to three images. Choose one with `SectionImage`:

| Name | Field in `section.optical_images` | Image |
|---|---|---|
| `SectionImage.POST_PICKUP` | `post_pickup_image` | Taken after the section is picked up |
| `SectionImage.POST_DROPOFF` | `post_dropoff_image` | Taken after the section is dropped off |
| `SectionImage.QC` | `qc_image` | Quality control image |

The client also accepts the field name as a string, and raises `ValueError` for any other name before sending a
request.

### Uploading

Pass a storage location with the first upload. A key with a leading slash is used as written:

```python
import asyncio

from temdb.client import TEMdbClient
from temdb.models import FileObjectRequest, SectionImage


async def main():
    location = FileObjectRequest(
        protocol="s3",
        server="https://s3.us-west-2.amazonaws.com",
        bucket="my-bucket",
        key="/001134/00113400_qc.jpeg",
    )
    async with TEMdbClient("http://temdb.example.com") as client:
        with open("00113400_qc.jpeg", "rb") as image:
            await client.section.put_image(section_id, SectionImage.QC, image, location)


asyncio.run(main())
```

If the block has a `default_storage`, or the server has a default, a key is enough:

```python
location = FileObjectRequest(key="001134/00113400_qc.jpeg")
```

To replace a stored image, delete it first. Uploading to a different location, or changing or clearing an image
through a section update, is refused so that no file is left behind in storage.

### Downloading

```python
image = await client.section.get_image(section_id, SectionImage.QC)

url = await client.section.get_image_url(section_id, SectionImage.QC, expiration=300)
print(url.url)
```

### Deleting

`delete_image` removes the file from storage and clears the field:

```python
await client.section.delete_image(section_id, SectionImage.QC)
```

A section with stored images cannot be deleted until its images are.

## Tile Images

A tile holds one image. The tile methods take the acquisition and tile ids instead of a name:

```python
with open("tile.tif", "rb") as image:
    await client.acquisition.put_image(acquisition_id, tile_id, image, location)

image = await client.acquisition.get_image(acquisition_id, tile_id)
```

## Credentials

Clients only need the signed URLs that TEMdb returns. The TEMdb server signs them with boto3's standard credentials,
such as environment variables or an AWS profile, so storage access is configured where the server runs.

## Older Section Images

Sections whose image paths could not be converted to a storage location keep them in
`extra["legacy_optical_images"]`, by their old names. These entries have no image routes.
