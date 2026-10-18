# Specimen Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `specimen_id` | string | Unique specimen identifier |
| `description` | string | Description of specimen, used for additional notes. |
| `specimen_images` | object | Images of specimen |
| `functional_imaging_metadata` | object | Functional imaging metadata of specimen, optional links to other datasets |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
