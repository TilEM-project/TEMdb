# Substrate Model

Document Mapping class.

Fields:

- `id` - MongoDB document ObjectID "_id" field.
Mapped to the PydanticObjectId class

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `media_id` | string | Primary unique identifier for this substrate (e.g., wafer ID, tape reel ID) |
| `media_type` | string | Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid') |
| `uid` | string | Overall unique identifier for the substrate instance (e.g., from XML uid) |
| `status` | string | Status of the entire substrate (e.g., new, in_use, full, retired, damaged) |
| `refpoint` | object | Reference points in local substrate coordinates |
| `refpoint_world` | object | Reference points mapped to world/stage coordinates |
| `source_path` | string | Path or identifier of the source file defining this substrate (e.g., XML path) |
| `metadata` | object | General metadata about the substrate |
| `apertures` | object[] | List of apertures or slots defined on this substrate, if applicable |
| `created_at` | datetime |  |
| `updated_at` | datetime |  |
