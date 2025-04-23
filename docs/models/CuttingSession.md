# CuttingSession Model

Document Mapping class.

Fields:

- `id` - MongoDB document ObjectID "_id" field.
Mapped to the PydanticObjectId class

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `cutting_session_id` | string | Unique, likely system-generated ID of cutting session |
| `specimen_id` | string | Human-readable ID of specimen (derived from Block) |
| `block_id` | string | Human-readable ID of block |
| `start_time` | datetime | Time when cutting session started |
| `end_time` | datetime | Time when cutting session ended |
| `operator` | string | Operator of cutting session |
| `sectioning_device` | string | Microtome/Device used for sectioning |
| `media_type` | string | Type of substrate the sections are placed upon |
| `knife_id` | string | Identifier for the knife used |
| `specimen_ref` | [Specimen](Specimen.md) | Internal link to the specimen document |
| `block_ref` | [Block](Block.md) | Internal link to the block document |
| `created_at` | datetime |  |
| `updated_at` | datetime |  |
