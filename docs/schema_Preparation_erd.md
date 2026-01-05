# Preparation Workflow Schema.

```mermaid
erDiagram
    direction LR
    AcquisitionDocument {
        object hardware_settings
        object acquisition_settings
        temdbmodelsacquisiti... calibration_info
        enum status
        float|None tilt_angle
        bool|None lens_correction
        datetimedatetime|Non... end_time
        listtemdbmodelsacqui... storage_locations
        str|None montage_set_name
        dictstrint|None sub_region
        int|None replaces_acquisition_id
        string acquisition_id
        string montage_id
        string specimen_id
        string roi_id
        string acquisition_task_id
        SpecimenDocument specimen_ref FK
        ROIDocument roi_ref FK
        AcquisitionTaskDocument acquisition_task_ref FK
        datetime start_time
    }
    AcquisitionTaskDocument {
        string task_type
        enum status
        str|None error_message
        datetimedatetime|Non... started_at
        datetimedatetime|Non... completed_at
        liststr|None tags
        dictstrtypingAny|Non... metadata
        string task_id
        string specimen_id
        string block_id
        string roi_id
        SpecimenDocument specimen_ref FK
        BlockDocument block_ref FK
        ROIDocument roi_ref FK
    }
    BlockDocument {
        dictstrtypingAny|Non... microCT_info
        string block_id
        string specimen_id
        SpecimenDocument specimen_ref FK
        str|None description
    }
    CuttingSessionDocument {
        datetime start_time
        datetimedatetime|Non... end_time
        str|None operator
        string sectioning_device
        string media_type
        str|None knife_id
        string cutting_session_id
        string specimen_id
        string block_id
        SpecimenDocument specimen_ref FK
        BlockDocument block_ref FK
    }
    ROIDocument {
        listfloat|None aperture_width_height
        listfloat|None aperture_centroid
        listfloat|None aperture_bounding_box
        str|None aperture_image
        float|None optical_pixel_size
        float|None scale_y
        int|str|None barcode
        listtypingAny|None rois
        str|None bucket
        str|None roi_mask
        str|None roi_mask_bucket
        dictstrtypingAny|Non... corners
        dictstrtypingAny|Non... corners_perpendicular
        str|None rule
        listtypingAny|None edits
        bool|None auto_roi
        dictstrtypingAny|Non... roi_parameters
        listtypingAny|None vertices
        string roi_id
        int roi_number
        string section_id
        string block_id
        string specimen_id
        string substrate_media_id
        int hierarchy_level
        SectionDocument section_ref FK
        ROIDocument parent_roi_ref FK
        int|None section_number
    }
    SectionDocument {
        int section_number
        datetime timestamp
        dictstrtypingAny|Non... optical_image
        str|None aperture_uid
        int|None aperture_index
        str|None barcode
        temdbmodelssectionSe... section_metrics
        string section_id
        string cutting_session_id
        string block_id
        string specimen_id
        string media_id
        CuttingSessionDocument cutting_session_ref FK
        SubstrateDocument substrate_ref FK
    }
    SpecimenDocument {
        str|None description
        setstr|None specimen_images
        dictstrtypingAny|Non... functional_imaging_metadata
        string specimen_id
    }
    SubstrateDocument {
        str|None uid
        str|None status
        temdbmodelssubstrate... refpoint
        temdbmodelssubstrate... refpoint_world
        str|None source_path
        temdbmodelssubstrate... metadata
        listtemdbmodelssubst... apertures
        string media_id
        string media_type
    }

    AcquisitionTaskDocument }o--|| AcquisitionDocument : acquisition_task_ref
    BlockDocument }o--|| AcquisitionTaskDocument : block_ref
    BlockDocument }o--|| CuttingSessionDocument : block_ref
    CuttingSessionDocument }o--|| SectionDocument : cutting_session_ref
    ROIDocument }o--|| AcquisitionDocument : roi_ref
    ROIDocument }o--|| AcquisitionTaskDocument : roi_ref
    ROIDocument }o--|| ROIDocument : parent_roi_ref
    SectionDocument }o--|| ROIDocument : section_ref
    SpecimenDocument }o--|| AcquisitionDocument : specimen_ref
    SpecimenDocument }o--|| AcquisitionTaskDocument : specimen_ref
    SpecimenDocument }o--|| BlockDocument : specimen_ref
    SpecimenDocument }o--|| CuttingSessionDocument : specimen_ref
    SubstrateDocument }o--|| SectionDocument : substrate_ref
```
