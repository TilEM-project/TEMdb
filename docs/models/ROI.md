# ROI Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `roi_id` | string | Hierarchical ID of ROI |
| `roi_number` | int | Sequential number for this ROI within its parent context |
| `section_id` | string | ID of section |
| `block_id` | string | ID of block |
| `specimen_id` | string | ID of specimen |
| `substrate_media_id` | string | Media ID of the substrate |
| `hierarchy_level` | int | Depth level in ROI hierarchy (1=top-level, 2=child, etc.) |
| `parent_roi_id` | string | Hierarchical ID of parent ROI |
| `dataset_id` | UUID | ID of the dataset this ROI belongs to |
| `section_number` | int | Number of section from collection |
| `roi_payload` | object | Domain attributes of the ROI |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
