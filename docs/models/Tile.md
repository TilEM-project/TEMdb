# Tile Model

Document Mapping class.

Fields:

- `id` - MongoDB document ObjectID "_id" field.
Mapped to the PydanticObjectId class

## Fields

| Field Name | Type | Description |
|------------|------|-------------|
| `tile_id` | string | ID of the tile |
| `acquisition_id` | string | ID of the acquisition |
| `acquisition_ref` | [Acquisition](Acquisition.md) | Internal link to the acquisition document |
| `raster_index` | int | Index of the tile in the raster |
| `stage_position` | object | Stage position of the tile in stage coordinates in nm |
| `raster_position` | object | Row, column raster position of the tile |
| `focus_score` | float | Focus score of the tile |
| `min_value` | float | Minimum pixel value of the tile |
| `max_value` | float | Maximum pixel value of the tile |
| `mean_value` | float | Mean pixel value of the tile |
| `std_value` | float | Standard deviation of pixel values of the tile |
| `image_path` | string | URL to the image of the tile |
| `matcher` | object[] | Matching data for the tile |
| `supertile_id` | string | ID of the supertile the tile belongs to |
| `supertile_raster_position` | object | Row, column raster position of the supertile |
