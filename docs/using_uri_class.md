# Using the URI Class

To help upload and download referenced files, import the `URI` class with `from temdb.models import URI`.

## Uploading Files

When uploading a new file, use this pattern:

```python
from temdb.models import URI

image_uri = URI("s3://random-bucket/my_image.png")

with open("./my_image.png", "rb") as infile:
    with image_uri.open("wb") as outfile:
        outfile.write(infile.read())
```

The data can come from any source, not only from existing files. Once the file is uploaded, store its `URI` in the
database. `TEMdbClient` is asynchronous, so call it from a coroutine:

```python
import asyncio

from temdb.client import TEMdbClient


async def main():
    async with TEMdbClient("http://temdb.example.com") as client:
        await client.specimen.create(specimen_id="my_dummy_specimen", specimen_images=[image_uri])


asyncio.run(main())
```

To add an image to an existing specimen, use `await client.specimen.add_image("my_dummy_specimen", str(image_uri))`.

## Downloading Files

Fields that hold URIs come back from the client as `URI` objects:

```python
async with TEMdbClient("http://temdb.example.com") as client:
    specimen = await client.specimen.get("my_dummy_specimen")

for image_uri in specimen.specimen_images:
    with image_uri.open("rb") as remote_file:
        with open("downloaded_image.png", "wb") as local_file:
            local_file.write(remote_file.read())
    break
```

The remote data can also be read directly instead of saved to a local file.

## Example URIs

The library underneath the `URI` class can write to several data stores. S3 and S3-compatible storage have been
tested. Some example URIs:

### AWS S3

`s3://bucket/object`

### Ceph

`s3u://:@aidc-ceph1-prd.corp.alleninstitute.org:8000@bucket/object`

## Credentials

By default, the `URI` class uses whatever credentials the system has installed for a given client. To use different
credentials for different storage systems or buckets, use a configuration file; see
[Data Configuration](data_config.md).
