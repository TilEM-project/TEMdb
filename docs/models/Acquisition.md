# Acquisition Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `acquisition_id` | string |  |
| `run_id` | UUID |  |
| `montage_id` | string |  |
| `specimen_id` | string |  |
| `roi_id` | string |  |
| `acquisition_task_id` | string |  |
| `microscope_id` | UUID |  |
| `dataset_id` | UUID |  |
| `kind` | string |  |
| `lc_id` | UUID |  |
| `hardware_settings` | object |  |
| `acquisition_settings` | object |  |
| `calibration_info` | object |  |
| `status` | string |  |
| `error_message` | string |  |
| `qc_state` | string |  |
| `qc_state_updated_at` | datetime |  |
| `qc_state_updated_by` | string |  |
| `transfer_state` | string |  |
| `transfer_state_updated_at` | datetime |  |
| `transfer_state_updated_by` | string |  |
| `tile_count` | int |  |
| `avg_focus_score` | float |  |
| `failed_tile_count` | int |  |
| `median_match_quality` | float |  |
| `tilt_angle_deg` | float |  |
| `start_time` | datetime |  |
| `end_time` | datetime |  |
| `storage_locations` | object |  |
| `montage_set_name` | string |  |
| `sub_region` | object |  |
| `replaces_acquisition_id` | string |  |
| `created_at` | datetime |  |
| `updated_at` | datetime |  |
