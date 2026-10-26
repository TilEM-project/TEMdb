# Section Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `section_id` | string | Unique, system-generated ID for the section |
| `section_number` | int | Number TEMdb assigned on the substrate, in create order |
| `cut_count` | int | Cut counter reported by the sectioning device; not unique, it can restart |
| `timestamp` | datetime | Timestamp of section creation/cutting |
| `cutting_session_id` | string | ID of the cutting session |
| `block_id` | string | ID of the block |
| `specimen_id` | string | ID of the specimen |
| `media_id` | string | ID of the substrate |
| `optical_image` | object | Images of the section by name, e.g. thumbnail, autotome_qc_snapshot, roi |
| `aperture_index` | int | Index of the layout aperture holding this section; empty for a section on a blank |
| `position` | object | Where the section sits on the substrate, if known |
| `condition` | string | Physical condition of the section |
| `condition_reason` | string | Reason for the current condition |
| `section_metrics` | object | Metrics and parameters of the section |
| `run_parameters` | object | Detailed parameters from the sectioning run |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
