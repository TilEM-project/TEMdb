# AcquisitionTask Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `task_id` | string | Unique identifier for this task |
| `specimen_id` | string | ID of specimen |
| `block_id` | string | ID of block |
| `roi_id` | string | ID of region of interest |
| `dataset_id` | UUID | Dataset this task belongs to (UUIDv7) |
| `kind` | string | Task kind: montage or lens_correction |
| `superseded_by` | string | task_id of the replacement task, if superseded |
| `task_group_id` | UUID | Group ID linking related tasks (e.g., a tilt series) |
| `tilt_angle_deg` | float | Planned tilt angle in degrees |
| `sub_region` | object | Planned sub-region of the ROI |
| `tags` | object | Tags for filtering |
| `metadata` | object | Additional metadata |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
