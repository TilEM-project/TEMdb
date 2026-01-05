from beanie import Document, Link
from pydantic import Field
from pymongo import ASCENDING, IndexModel
from temdb.models import TileBase

from .acquisition import AcquisitionDocument


class TileDocument(Document, TileBase):
    """MongoDB document for tile data."""

    tile_id: str = Field(..., description="ID of the tile")
    acquisition_id: str = Field(..., description="ID of the acquisition")
    acquisition_ref: Link[AcquisitionDocument] = Field(..., description="Internal link to the acquisition document")
    raster_index: int = Field(..., description="Index of the tile in the raster")

    # Override base fields that are required in document
    stage_position: dict[str, float] = Field(..., description="Stage position of the tile in stage coordinates in nm")
    raster_position: dict[str, int] = Field(..., description="Row, column raster position of the tile")
    focus_score: float = Field(..., description="Focus score of the tile")
    min_value: float = Field(..., description="Minimum pixel value of the tile")
    max_value: float = Field(..., description="Maximum pixel value of the tile")
    mean_value: float = Field(..., description="Mean pixel value of the tile")
    std_value: float = Field(..., description="Standard deviation of pixel values of the tile")
    image_path: str = Field(..., description="URL to the image of the tile")

    class Settings:
        name = "tiles"
        indexes = [
            IndexModel([("tile_id", ASCENDING)], unique=True, name="tile_id_index"),
            IndexModel([("acquisition_id", ASCENDING)], name="acquisition_id_index"),
            IndexModel([("acquisition_ref.id", ASCENDING)], name="acquisition_ref_index"),
            IndexModel(
                [("acquisition_ref.id", ASCENDING), ("raster_index", ASCENDING)],
                name="acquisition_raster_index",
            ),
            IndexModel([("supertile_id", ASCENDING)], name="supertile_id_index"),
            IndexModel([("focus_score", ASCENDING)], name="focus_score_index", sparse=True),
        ]
