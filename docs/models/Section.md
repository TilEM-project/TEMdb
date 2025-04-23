# Section Model

Document Mapping class.

Fields:

- `id` - MongoDB document ObjectID "_id" field.
Mapped to the PydanticObjectId class

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `section_id` | string | Unique, likely system-generated ID for the section (e.g., MEDIAID_SXXXX) |
| `section_number` | int | Sequential section number within the cutting session |
| `timestamp` | datetime | Timestamp of section creation/cutting |
| `cutting_session_id` | string | Human-readable ID of the cutting session |
| `block_id` | string | Human-readable ID of the block |
| `specimen_id` | string | Human-readable ID of the specimen |
| `media_id` | string | Human-readable ID of the substrate |
| `cutting_session_ref` | [CuttingSession](CuttingSession.md) | Internal Link to the cutting session document |
| `substrate_ref` | [Substrate](Substrate.md) | Internal Link to the substrate document |
| `aperture_uid` | string | UID of the specific aperture holding this section |
| `aperture_index` | int | Index of the specific aperture holding this section |
| `barcode` | string | Barcode for this section, if any |
| `optical_image` | object | Metadata about optical image |
| `section_metrics` | object | Metrics and parameters of the section |
| `created_at` | datetime |  |
| `updated_at` | datetime |  |
