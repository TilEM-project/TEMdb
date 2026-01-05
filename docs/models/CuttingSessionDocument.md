# CuttingSessionDocument Model

MongoDB document for cutting session data.

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `start_time` | datetime | Time when cutting session started |
| `end_time` | datetimedatetime|Non... | Time when cutting session ended |
| `operator` | str|None | Operator of cutting session |
| `sectioning_device` | string | Microtome/Device used for sectioning |
| `media_type` | string | Type of substrate the sections are placed upon |
| `knife_id` | str|None | Identifier for the knife used |
| `cutting_session_id` | string | Unique ID of cutting session |
| `specimen_id` | string | Human-readable ID of specimen |
| `block_id` | string | Human-readable ID of block |
| `specimen_ref` | [SpecimenDocument](SpecimenDocument.md) | Internal link to the specimen document |
| `block_ref` | [BlockDocument](BlockDocument.md) | Internal link to the block document |
| `created_at` | datetime |  |
| `updated_at` | datetimedatetime|Non... |  |
