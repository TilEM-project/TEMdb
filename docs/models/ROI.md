# ROI Model

Document Mapping class.

Fields:

- `id` - MongoDB document ObjectID "_id" field.
Mapped to the PydanticObjectId class

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `roi_id` | int | Unique, human-readable integer ID for this ROI |
| `section_id` | string | Human-readable ID of the parent Section |
| `cutting_session_id` | string | Human-readable ID of the parent Cutting Session |
| `block_id` | string | Human-readable ID of the parent Block |
| `specimen_id` | string | Human-readable ID of the parent Specimen |
| `section_ref` | [Section](Section.md) | Internal link to the section document |
| `parent_roi_ref` | [ROI](ROI.md) | Internal link to the parent ROI document, if any |
| `section_number` | int |  |
| `aperture_width_height` | any[] |  |
| `aperture_centroid` | any[] |  |
| `aperture_bounding_box` | any[] |  |
| `aperture_image` | string |  |
| `optical_pixel_size` | float |  |
| `scale_y` | float |  |
| `barcode` | int |  |
| `rois` | any[] |  |
| `bucket` | string |  |
| `roi_mask` | string |  |
| `roi_mask_bucket` | string |  |
| `corners` | object |  |
| `corners_perpendicular` | object |  |
| `rule` | string |  |
| `edits` | any[] |  |
| `auto_roi` | bool |  |
| `roi_parameters` | object |  |
| `updated_at` | datetime | Time of last update |
