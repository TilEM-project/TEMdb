# Using the URI Class

To aid in uploading an downloading referenced files, a `URI` class can be imported using `from temdb.models import URI`. This class can be used in the following ways.

## Uploading Files

When uploading a new file, the following pattern can be used.

```python
from temdb.models import URI

image_uri = URI("s3://random-bucket/my_image.png")

with open("./my_image.png", "rb") as infile:
   with image_uri.open("wb") as outfile:
      outfile.write(infile.read())
```

Of course, the data can come from any source, not just from existing files. Once a `URI` class instance has been created, it can be passed be uploaded to the database. For example:

```python
from temdb.client import create_client
from temdb.models import SpecimenCreate

client = create_client("http://temdb.example.com", async_mode=False)

client.specimen.create(SpecimenCreate(
   specimen_id="my_dummy_specimen",
   specimen_images=[image_uri],
))
```

## downloading Files

When querying data from the database, `URI` objects are automatically returned. For example,

```python
specimen = client.specimen.get("my_dummy_specimen")

for image_uri in specimen.specimen_images:
   with image_uri.open() as remote_file:
      with open("downloaded_image.png", "wb") as local_file:
         local_file.write(remote_file.read())
   break
```

Of course, the remote file data could be read directly, rather than saved to a local file.

## Example URIs

The underlying library the `URI` class uses can write to multiple data stores. So far, S3 and S3 compatible storage has been tested. Below are a few example URIs.

### AWS S3

`s3://bucket/object`

### Ceph

`s3u://:@aidc-ceph1-prd.corp.alleninstitute.org:8000@bucket/object`

## Credentials

By default, the URI class will use whatever credentials the system has installed for a given client. In order to support different credentials for different storage systems or buckets, a configuration file can be used. More information about this configuration file is available [here](data_config.md).
