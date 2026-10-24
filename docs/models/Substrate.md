# Substrate Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `media_id` | string | Primary unique identifier |
| `substrate_layout_id` | string | The ID of the substrate layout |
| `aperture_status` | list | Status of each aperture in layout order |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
