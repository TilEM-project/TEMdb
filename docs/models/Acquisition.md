# Acquisition Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `acquisition_id` | string | Unique acquisition identifier |
| `run_id` | UUID | DB-minted UUIDv7 execution key |
| `montage_id` | string | Montage identifier |
| `specimen_id` | string | Specimen identifier |
| `roi_id` | string | ROI identifier |
| `acquisition_task_id` | string | Parent task identifier |
| `microscope_id` | string | Microscope that executed this run |
| `dataset_id` | UUID | Dataset this acquisition belongs to (UUIDv7) |
| `kind` | string | Run kind: montage or lens_correction |
| `lc_id` | UUID | Lens correction applied to this run |
| `hardware_settings` | object | Hardware settings of acquisition |
| `acquisition_settings` | object | Acquisition settings of acquisition |
| `calibration_info` | object |  |
| `status` | string | Terminal run status; null while in flight |
| `error_message` | string | Failure detail for terminal status |
| `qc_state` | string | QC axis state |
| `qc_state_updated_at` | datetime |  |
| `qc_state_updated_by` | string |  |
| `transfer_state` | string | Transfer axis state |
| `transfer_state_updated_at` | datetime |  |
| `transfer_state_updated_by` | string |  |
| `tile_count` | int |  |
| `avg_focus_score` | float |  |
| `failed_tile_count` | int |  |
| `median_match_quality` | float |  |
| `tilt_angle_deg` | float | Tilt angle of acquisition in degrees |
| `start_time` | datetime | Start time of acquisition |
| `end_time` | datetime | End time of acquisition |
| `storage_locations` | object | Storage locations of acquisition |
| `montage_set_name` | string | Name of montage set |
| `sub_region` | object | Sub region of acquisition |
| `replaces_acquisition_id` | string | Business ID (acquisition_id) of acquisition this acquisition replaces |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
