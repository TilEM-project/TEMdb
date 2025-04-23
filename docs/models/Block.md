# Block Model

Document Mapping class.

Fields:

- `id` - MongoDB document ObjectID "_id" field.
Mapped to the PydanticObjectId class

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `block_id` | string | Block ID of specimen |
| `microCT_info` | object | MicroCT information of block |
| `specimen_ref` | [Specimen](Specimen.md) | ID of specimen |
| `specimen_id` | string | Human-readable ID of the parent Specimen |
