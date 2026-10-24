# ROI Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `roi_id` | string | {media_id}.A{aperture:04d}.R{roi_number:03d}, or {media_id}.R{roi_number:04d} on a section with no aperture; set by TEMdb |
| `roi_number` | int | Number TEMdb assigned on the aperture (or on the substrate, with no aperture), in create order |
| `section_id` | string | The section the ROI is drawn on |
| `substrate_media_id` | string | Media ID of the substrate |
| `aperture_index` | int | Index of the layout aperture; none for a section off apertures |
| `parent_roi_id` | string | ID of the parent ROI |
| `dataset_id` | UUID | ID of the dataset this ROI belongs to |
| `roi_payload` | object | Domain attributes of the ROI |
| `created_at` | datetime | When the ROI was created |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
