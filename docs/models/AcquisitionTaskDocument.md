# AcquisitionTaskDocument Model

MongoDB document for acquisition task data.

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `task_type` | string | Type of acquisition task |
| `version` | int | Version number of this task |
| `status` | enum |  |
| `error_message` | str|None | Error message if failed |
| `started_at` | datetimedatetime|Non... | When task execution began |
| `completed_at` | datetimedatetime|Non... | When task finished (success or failure) |
| `tags` | liststr|None | Tags for filtering |
| `metadata` | dictstrtypingAny|Non... | Additional metadata |
| `task_id` | string | Unique identifier for this task |
| `specimen_id` | string | ID of specimen |
| `block_id` | string | ID of block |
| `roi_id` | string | ID of region of interest to be acquired |
| `specimen_ref` | [SpecimenDocument](SpecimenDocument.md) | Internal link to the specimen document |
| `block_ref` | [BlockDocument](BlockDocument.md) | Internal link to the block document |
| `roi_ref` | [ROIDocument](ROIDocument.md) | Internal link to the region of interest document |
| `created_at` | datetime |  |
| `updated_at` | datetimedatetime|Non... | When task was last updated |
