# Acquisition Model

Document Mapping class.

Fields:

- `id` - MongoDB document ObjectID "_id" field.
Mapped to the PydanticObjectId class

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `acquisition_id` | string | ID of acquisition |
| `montage_id` | string | ID of montage |
| `specimen_id` | string | ID of specimen |
| `roi_id` | int | ID of region of interest |
| `acquisition_task_id` | string | ID of acquisition task |
| `specimen_ref` | [Specimen](Specimen.md) | Internal link to the specimen document |
| `roi_ref` | [ROI](ROI.md) | Internal link to the region of interest document |
| `acquisition_task_ref` | [AcquisitionTask](AcquisitionTask.md) | Internal link to the acquisition task document |
| `hardware_settings` | object | Hardware settings of acquisition |
| `acquisition_settings` | object | Acquisition settings of acquisition |
| `calibration_info` | object | Calibration information of acquisition |
| `status` | enum | Status of acquisition |
| `tilt_angle` | float | Tilt angle of acquisition in degrees |
| `lens_correction` | bool | Whether this acquisition is a lens correction calibration |
| `start_time` | datetime | Start time of acquisition |
| `end_time` | datetime | End time of acquisition |
| `storage_locations` | object[] | Storage locations of acquisition |
| `montage_set_name` | string | Name of montage set |
| `sub_region` | object | Sub region of acquisition |
| `replaces_acquisition_id` | int | ID of acquisition this acquisition replaces |
