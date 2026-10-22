# Tile Model

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `dataset_id` | UUID |  |
| `run_id` | UUID |  |
| `row` | int |  |
| `col` | int |  |
| `retake` | int | Capture number at this position within the run; 0 is the first |
| `raster_index` | int | Index of the tile in the raster |
| `stage_x_nm` | float |  |
| `stage_y_nm` | float |  |
| `stage_z_nm` | float |  |
| `focus_score` | float | Focus score of the tile |
| `min_value` | float | Minimum pixel value of the tile |
| `max_value` | float | Maximum pixel value of the tile |
| `mean_value` | float | Mean pixel value of the tile |
| `std_value` | float | Standard deviation of pixel values of the tile |
| `image_path` | string | URL to the image of the tile |
| `matcher` | object | List of matchers for the tile |
| `supertile_id` | string | ID of the supertile the tile belongs to |
| `supertile_raster_position` | object | Row, column raster position of the supertile |
| `created_at` | datetime |  |
| `updated_at` | datetime |  |
