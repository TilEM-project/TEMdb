# BlockDocument Model

MongoDB document for block data.

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `microCT_info` | dictstrtypingAny|Non... | MicroCT information of block |
| `block_id` | string | ID of the block within the specimen |
| `specimen_id` | string | ID of specimen this block belongs to |
| `specimen_ref` | [SpecimenDocument](SpecimenDocument.md) | Internal link to the specimen document |
| `description` | str|None | Description of the block |
| `created_at` | datetime | Time when block metadata was created |
| `updated_at` | datetimedatetime|Non... | Time when block metadata was last updated |
