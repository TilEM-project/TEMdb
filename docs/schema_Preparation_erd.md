# Preparation Workflow Schema.

```mermaid
erDiagram
    direction LR
    BlockSQLModel ||--o{ CuttingSessionSQLModel : "specimen_id, block_id"
    BlockSQLModel ||--o{ SectionSQLModel : "specimen_id, block_id"
    CuttingSessionSQLModel ||--o{ SectionSQLModel : "cutting_session_id"
    SpecimenSQLModel ||--o{ BlockSQLModel : "specimen_id"
    SubstrateSQLModel ||--o{ SectionSQLModel : "media_id"
    BlockSQLModel {
        string block_id
        string specimen_id
        object microCT_info
    }
    CuttingSessionSQLModel {
        string cutting_session_id
        string specimen_id
        string block_id
        datetime start_time
        datetime end_time
        string operator
        string sectioning_device
        string media_type
        string knife_id
    }
    SectionSQLModel {
        string section_id
        int section_number
        datetime timestamp
        string cutting_session_id
        string block_id
        string specimen_id
        string media_id
        object optical_image
        string aperture_uid
        int aperture_index
        string barcode
        string condition
        string condition_reason
        object section_metrics
    }
    SpecimenSQLModel {
        string specimen_id
        string description
        object specimen_images
        object functional_imaging_metadata
    }
    SubstrateSQLModel {
        string media_id
        string media_type
        string uid
        string status
        object refpoint
        object refpoint_world
        string source_path
        object metadata
        object apertures
    }
```