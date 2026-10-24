# Microscope Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `microscope_id` | string | Unique readable identifier, e.g. 'T1' |
| `microscope_type` | string | Instrument type |
| `model` | string | Manufacturer model |
| `location` | string | Physical location |
| `notes` | string | Free-form notes |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
