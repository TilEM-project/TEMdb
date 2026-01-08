from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from temdb.models.acquisition import LensCorrectionModel
from temdb.models.tile import TileResponse


class TileSpecMetadata(BaseModel):
    """Montage-level metadata for TileSpec construction."""

    model_config = ConfigDict(extra="allow")

    montage_id: str = Field(..., description="Unique montage identifier")

    width: int = Field(..., description="Tile width in pixels")
    height: int = Field(..., description="Tile height in pixels")

    saved_bit_depth: int = Field(..., description="Bit depth of saved images")

    pixel_size: float = Field(..., description="Pixel size in nm")
    rotation_angle: float = Field(..., description="Rotation angle in degrees")
    lens_model: LensCorrectionModel | None = Field(None, description="Lens correction model")

    scope_id: str = Field(..., description="Microscope ID (tilespec scopeId)")
    camera_serial: str = Field(..., description="Camera serial number (tilespec cameraId)")
    section_id: str = Field(..., description="Section ID (tilespec sectionId)")

    section_number: int = Field(..., description="Section number for z derivation")
    media_id: str = Field(..., description="Media ID for z/groupId derivation")
    roi_id: str = Field(..., description="ROI ID")
    specimen_id: str = Field(..., description="Specimen ID")

    storage_base_path: str | None = Field(None, description="Base path for image storage")

    tilt_angle: float | None = Field(None, description="Tilt angle for tomography in degrees")


class PaginatedTileResponse(BaseModel):
    """Paginated response for tile list."""

    tiles: list[TileResponse]
    metadata: dict[str, Any]


@dataclass
class AsyncTileSpecData:
    """
    Combined metadata and tile iterator for async TileSpec generation.

    Usage:
        result = await client.montage.get_tilespec_data("MONTAGE_001")
        async for tile in result.tiles:
            tilespec = some_tilespec_builder_method(result.metadata, tile)
    """

    metadata: TileSpecMetadata
    tiles: AsyncIterator[TileResponse]


@dataclass
class TileSpecData:
    """
    Combined metadata and tile iterator for sync TileSpec generation.

    Usage:
        result = client.montage.get_tilespec_data("MONTAGE_001")
        for tile in result.tiles:
            tilespec = some_tilespec_builder_method(result.metadata, tile)
    """

    metadata: TileSpecMetadata
    tiles: Iterator[TileResponse]
