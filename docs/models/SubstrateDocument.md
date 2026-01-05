# SubstrateDocument Model

MongoDB document for substrate data.

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `uid` | str|None | Overall unique identifier for the substrate instance |
| `status` | str|None | Status of the entire substrate (e.g., new, in_use, full, retired, damaged) |
| `refpoint` | temdbmodelssubstrate... | Reference points in local substrate coordinates |
| `refpoint_world` | temdbmodelssubstrate... | Reference points mapped to world/stage coordinates |
| `source_path` | str|None | Path or identifier of the source file defining this substrate |
| `metadata` | temdbmodelssubstrate... | General metadata about the substrate |
| `apertures` | listtemdbmodelssubst... | List of apertures or slots defined on this substrate |
| `media_id` | string | Primary unique identifier for this substrate (e.g., wafer ID, tape reel ID) |
| `media_type` | string | Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid') |
| `created_at` | datetime |  |
| `updated_at` | datetimedatetime|Non... |  |
