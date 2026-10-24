# Block Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `block_id` | string | Unique block identifier |
| `specimen_id` | string | Parent specimen ID |
| `microCT_info` | object | MicroCT information of block |
| `default_storage` | object | Default storage for sections in this block |
| `description` | string | Description of block |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
