# SubstrateLayout Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `layout_id` | string | Overall unique identifier for the substrate layout |
| `name` | string | Human readable name of the substrate layout |
| `fiducials` | object | List of fiducials on the substrate |
| `apertures` | object | Apertures in index order: apertures[i] is aperture i |
| `media_type` | string | Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid') |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
