# Data Configuration

TEMdb uses a configuration file to manage access to data storage locations, such as AWS S3 buckets and S3-compatible storage systems (e.g., Ceph).

## Location

The `data_config` file should be placed in your user configuration directory:

- **Linux:** `~/.config/TEMdb/data_config.yaml` or `~/.config/TEMdb/data_config.yml`
- **macOS:** `~/Library/Application Support/TEMdb/data_config.yaml` or `~/Library/Application Support/TEMdb/data_config.yml`
- **Windows:** `C:\Users\<User>\AppData\Local\TilEM\TEMdb\data_config.yaml` or `C:\Users\<User>\AppData\Local\TilEM\TEMdb\data_config.yml`

If the file is not found, TEMdb will operate with default settings and will not have configured access to data locations.

## File Format

The configuration file is in YAML format and contains a top-level `data_locations` key, which is a list of storage location configurations.

## Configuration Structure

### Basic Structure

```yaml
data_locations:
  - transport: s3
    # S3-specific configuration
  - transport: s3
    # Another S3 location
```

### S3 Storage Location

Each S3 storage location supports the following configuration options:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `transport` | string | Yes | Must be `"s3"` to specify S3/S3-compatible storage |
| `bucket` | string | No | Name of the bucket |
| `host` | string | No | Hostname of S3-compatible service (e.g., `ceph.example.com`). Default: AWS S3 endpoint |
| `port` | integer | No | Port number for S3 service. Default: `443` |
| `region` | string | No | AWS region. Default: `"us-east-1"` |
| `access_key_id` | string | No | Access key ID for authentication |
| `secret_access_key` | string | No | Secret access key for authentication |
| `use_ssl` | boolean | No | Whether to use SSL/TLS for connections. Default: `true` |

## Examples

### AWS S3 with Credentials

```yaml
data_locations:
  - transport: s3
    bucket: my-data-bucket
    region: us-west-2
    access_key_id: AKIAIOSFODNN7EXAMPLE
    secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
```

### Ceph S3-Compatible Storage with SSL

```yaml
data_locations:
  - transport: s3
    host: ceph.corp.example.org
    port: 443
    region: us-east-1
    access_key_id: ceph_user
    secret_access_key: ceph_secret_key
    use_ssl: true
```

### Ceph S3-Compatible Storage without SSL

```yaml
data_locations:
  - transport: s3
    host: ceph-internal.local
    port: 8000
    region: us-east-1
    access_key_id: ceph_user
    secret_access_key: ceph_secret_key
    use_ssl: false
```

### Multiple Storage Locations

```yaml
data_locations:
  # Production data in AWS
  - transport: s3
    bucket: production-data
    region: us-west-2
    access_key_id: PROD_KEY_ID
    secret_access_key: PROD_SECRET_KEY

  # Development data in Ceph
  - transport: s3
    host: ceph-dev.internal
    port: 9000
    region: us-east-1
    access_key_id: dev_user
    secret_access_key: dev_secret_key
    use_ssl: false

  # Backup in AWS different region
  - transport: s3
    bucket: backup-data
    region: us-east-1
    access_key_id: BACKUP_KEY_ID
    secret_access_key: BACKUP_SECRET_KEY
```

## How TEMdb Uses the Configuration

When TEMdb encounters a URI (e.g., an S3 path in a data field):

1. **Parses the URI** to extract location information (bucket, host, port, region, etc.)
2. **Matches against configurations** in the `data_config` file to find a matching location
3. **Uses the matching configuration** to:
   - Set up authentication credentials
   - Configure the S3 client with the appropriate endpoint, region, and SSL settings
   - Establish a connection to the storage system

### URI Matching Logic

Matching is based on the following priorities:

- **For AWS S3 URIs** (e.g., `s3://bucket-name/path`): Matches by bucket name
- **For S3-compatible URIs** (e.g., `s3u://:@host:port@bucket/path`): Matches by host and optionally port
- **First match wins**: If multiple configurations could apply, the first matching one in the file is used

### Client Caching

To improve performance, TEMdb caches the S3 client for each data location. Once a client is created for a location, subsequent accesses reuse the same client instance rather than creating a new one.

## Security Considerations

- **Credentials in Configuration:** Store your credentials securely. The configuration file should have restrictive file permissions (e.g., `chmod 600`).
- **Environment Variables:** Consider using environment variables for sensitive credentials and loading them into the configuration programmatically.
- **Secrets Management:** For production deployments, use your organization's secrets management system rather than storing credentials directly in the file.

## Error Handling

If the `data_config` file cannot be found or parsed:

- TEMdb will log a debug message but continue operation
- Access to storage locations will not be configured
- URIs without matching configurations will default to any default AWS credentials available
