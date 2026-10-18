# Dataset Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `dataset_id` | UUID | UUIDv7 primary key |
| `name` | string | Unique human-readable dataset name |
| `description` | string | Human description of the dataset |
| `specimen_id` | string | Specimen this dataset belongs to |
| `parent_dataset_id` | UUID | Parent dataset if this is a child (one level only) |
| `status` | string | Lifecycle status |
| `collected_at` | datetime |  |
| `archived_at` | datetime |  |
| `size_class` | string | Planner size class; drives tile partitioning |
| `tile_hash_modulus` | int | System-managed frozen partition modulus |
| `estimated_tile_count` | int | Estimated total tiles recorded at creation |
| `metadata_json` | object | Free-form metadata |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
