# AcquisitionDocument Model

MongoDB document for acquisition data.

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `hardware_settings` | object | Hardware settings of acquisition |
| `acquisition_settings` | object | Acquisition settings of acquisition |
| `calibration_info` | temdbmodelsacquisiti... |  |
| `status` | enum | Status of acquisition |
| `tilt_angle` | float|None | Tilt angle of acquisition in degrees |
| `lens_correction` | bool|None | Whether this acquisition is a lens correction calibration |
| `end_time` | datetimedatetime|Non... | End time of acquisition |
| `storage_locations` | listtemdbmodelsacqui... | Storage locations of acquisition |
| `montage_set_name` | str|None | Name of montage set |
| `sub_region` | dictstrint|None | Sub region of acquisition |
| `replaces_acquisition_id` | int|None | ID of acquisition this acquisition replaces |
| `acquisition_id` | string | ID of acquisition |
| `montage_id` | string | ID of montage |
| `specimen_id` | string | ID of specimen |
| `roi_id` | string | ID of region of interest |
| `acquisition_task_id` | string | ID of acquisition task |
| `specimen_ref` | [SpecimenDocument](SpecimenDocument.md) | Internal link to the specimen document |
| `roi_ref` | [ROIDocument](ROIDocument.md) | Internal link to the region of interest document |
| `acquisition_task_ref` | [AcquisitionTaskDocument](AcquisitionTaskDocument.md) | Internal link to the acquisition task document |
| `start_time` | datetime | Start time of acquisition |
