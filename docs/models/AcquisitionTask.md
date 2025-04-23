# AcquisitionTask Model

Document Mapping class.

Fields:

- `id` - MongoDB document ObjectID "_id" field.
Mapped to the PydanticObjectId class

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `task_id` | string | Unique identifier for this task |
| `specimen_id` | string | ID of specimen |
| `block_id` | string | ID of block |
| `roi_id` | int | ID of region of interest to be acquired |
| `task_type` | string | Type of acquisition task |
| `version` | int | Version number of this task |
| `specimen_ref` | [Specimen](Specimen.md) | Internal link to the specimen document |
| `block_ref` | [Block](Block.md) | Internal link to the block document |
| `roi_ref` | [ROI](ROI.md) | Internal link to the region of interest document |
| `status` | enum |  |
| `created_at` | datetime |  |
| `updated_at` | datetime | When task was last updated |
| `started_at` | datetime | When task execution began |
| `completed_at` | datetime | When task finished (success or failure) |
| `error_message` | string | Error message if failed |
| `tags` | string[] | Tags for filtering |
| `metadata` | object | Additional metadata |
