# ROIDocument Model

MongoDB document for ROI data.

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `aperture_width_height` | listfloat|None | Width and height of aperture in mm calculated from aperture_image |
| `aperture_centroid` | listfloat|None | Center of aperture measured in pixel coordinates from aperture_image |
| `aperture_bounding_box` | listfloat|None | Bounding box of aperture measured in pixel coordinates |
| `aperture_image` | str|None | URL of aperture image |
| `optical_pixel_size` | float|None | Optical resolution in nm per pixel |
| `scale_y` | float|None | Scaling factor for y-axis |
| `barcode` | int|str|None | Barcode of ROI if present |
| `rois` | listtypingAny|None | List of ROIs |
| `bucket` | str|None | Bucket of ROI |
| `roi_mask` | str|None | URL of ROI mask |
| `roi_mask_bucket` | str|None | Bucket of ROI mask |
| `corners` | dictstrtypingAny|Non... | Corners of ROI |
| `corners_perpendicular` | dictstrtypingAny|Non... | Perpendicular corners of ROI |
| `rule` | str|None | Rule for ROI corner detection |
| `edits` | listtypingAny|None | List of edits to ROI |
| `auto_roi` | bool|None | Flag if auto generated ROI was used |
| `roi_parameters` | dictstrtypingAny|Non... | Parameters of ROI |
| `vertices` | listtypingAny|None | Vertices of the ROI polygon |
| `roi_id` | string | Hierarchical, globally unique ID (e.g., 'SPEC001.BLK001.SEC001.SUB001.ROI001') |
| `roi_number` | int | Sequential number for this ROI within its parent context |
| `section_id` | string | Human-readable ID of the parent Section |
| `block_id` | string | Human-readable ID of the parent Block |
| `specimen_id` | string | Human-readable ID of the parent Specimen |
| `substrate_media_id` | string | Media ID of the substrate this section is placed on |
| `hierarchy_level` | int | Depth level in ROI hierarchy (1=top-level section ROI, 2=child ROI, etc.) |
| `section_ref` | [SectionDocument](SectionDocument.md) | Internal link to the section document |
| `parent_roi_ref` | [ROIDocument](ROIDocument.md) | Internal link to the parent ROI document, if any |
| `section_number` | int|None |  |
| `updated_at` | datetimedatetime|Non... | Time of last update |
