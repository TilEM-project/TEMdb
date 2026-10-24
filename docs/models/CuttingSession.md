# CuttingSession Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `cutting_session_id` | string | Unique cutting session identifier |
| `specimen_id` | string | ID of specimen |
| `block_id` | string | ID of block |
| `start_time` | datetime | Time when cutting session started |
| `end_time` | datetime | Time when cutting session ended |
| `operator` | string | Operator of cutting session |
| `sectioning_device` | string | Device used for sectioning |
| `media_type` | string | Type of substrate the sections are placed upon |
| `knife_id` | string | Identifier for the knife used |
| `created_at` | datetime | Creation timestamp; server-generated if omitted |
| `updated_at` | datetime |  |
| `extra` | object | Free-form fields outside the schema; an update merges keys and null removes one |
