# Specimen Model

Document Mapping class.

Fields:

- `id` - MongoDB document ObjectID "_id" field.
Mapped to the PydanticObjectId class

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `specimen_id` | string | ID of specimen |
| `description` | string | Description of specimen, used for additional notes. |
| `specimen_images` | string[] | Images of specimen |
| `created_at` | datetime | Time when specimen metadata was created |
| `updated_at` | datetime | Time when specimen metadata was last updated |
| `functional_imaging_metadata` | object | Functional imaging metadata of specimen, optional links to other datasets |
