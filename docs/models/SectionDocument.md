# SectionDocument Model

MongoDB document for section data.

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `section_number` | int | Sequential section number within the cutting session |
| `timestamp` | datetime | Timestamp of section creation/cutting |
| `optical_image` | dictstrtypingAny|Non... | Metadata about optical image collected before imaging |
| `aperture_uid` | str|None | UID of the specific aperture holding this section |
| `aperture_index` | int|None | Index of the specific aperture holding this section |
| `barcode` | str|None | Barcode scanned for this section, if any |
| `section_metrics` | temdbmodelssectionSe... | Metrics and parameters of the section |
| `section_id` | string | Unique, system-generated ID for the section (e.g., MEDIAID_SXXXX) |
| `cutting_session_id` | string | Human-readable ID of the cutting session |
| `block_id` | string | Human-readable ID of the block |
| `specimen_id` | string | Human-readable ID of the specimen |
| `media_id` | string | Human-readable ID of the substrate |
| `cutting_session_ref` | [CuttingSessionDocument](CuttingSessionDocument.md) | Internal Link to the cutting session document |
| `substrate_ref` | [SubstrateDocument](SubstrateDocument.md) | Internal Link to the substrate document |
| `created_at` | datetime |  |
| `updated_at` | datetimedatetime|Non... |  |
