# SpecimenDocument Model

MongoDB document for specimen data.

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `description` | str|None | Description of specimen, used for additional notes. |
| `specimen_images` | setstr|None | Images of specimen |
| `functional_imaging_metadata` | dictstrtypingAny|Non... | Functional imaging metadata of specimen, optional links to other datasets |
| `specimen_id` | string | ID of specimen |
| `created_at` | datetime | Time when specimen metadata was created |
| `updated_at` | datetimedatetime|Non... | Time when specimen metadata was last updated |
