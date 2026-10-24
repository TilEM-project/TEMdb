# LensCorrection Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `lc_id` | UUID | Optional client-supplied UUIDv7 |
| `microscope_id` | string |  |
| `magnification` | int |  |
| `started_at` | datetime |  |
| `source_run_id` | UUID |  |
| `source_dataset_id` | UUID |  |
| `shared_transform` | object |  |
| `correction_x_uri` | string |  |
| `correction_y_uri` | string |  |
| `solver_params` | object |  |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
