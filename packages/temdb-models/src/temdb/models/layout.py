from datetime import datetime

from pydantic import ConfigDict, Field, model_validator

from .base import TEMDBModel, TEMDBRecord
from .enums import ShapeType, SubstrateType


class CircleParams(TEMDBModel):
    diameter: float = Field(..., description="Diameter of the circle in mm")


class SlotParams(TEMDBModel):
    width: float = Field(..., description="Width of the slot in mm")
    height: float = Field(..., description="Height of the slot in mm")
    angle: float = Field(0, description="Angle of the slot in degrees (default: 0)")


class RectangleParams(TEMDBModel):
    width: float = Field(..., description="Width of the rectangle in mm")
    height: float = Field(..., description="Height of the rectangle in mm")
    corner_radius: float = Field(0, description="Corner radius of the rectangle in mm (default: 0)")
    angle: float = Field(0, description="Angle of the rectangle in degrees (default: 0)")


class TriangleParams(TEMDBModel):
    base: float = Field(..., description="Base of the triangle in mm")
    height: float | None = Field(None, description="Hieight of the triangle in mm or None if equilateral")
    corner_radius: float = Field(0, description="Corner radius of the triangle in mm (default: 0)")
    angle: float = Field(0, description="Angle of the triangle in degrees (default: 0)")


class CircleArrayParams(TEMDBModel):
    diameter: float = Field(..., description="Diameter of each circle in the array in mm")
    count: int | tuple[int, int] = Field(
        ..., description="Count of circles in the array; can be a single integer or a tuple for rows and columns"
    )
    pitch: float | tuple[float, float] = Field(
        ..., description="Pitch of the circles in the array; can be a single float or a tuple for X and Y pitch"
    )
    angle: float = Field(0, description="Angle of the circle array in degrees (default: 0)")


class PolygonParams(TEMDBModel):
    vertices: list[tuple[float, float]] = Field(
        ..., min_length=3, description="Polygon vertices (X, Y) in mm, relative to the centroid"
    )


class Shape(TEMDBModel):
    shape_type: ShapeType = Field(..., description="The type of shape")
    shape_params: CircleParams | SlotParams | RectangleParams | TriangleParams | CircleArrayParams | PolygonParams = (
        Field(..., description="Parameters of the shape")
    )
    centroid: tuple[float, float] = Field(..., description="Centroid of the shape (X, Y) in mm")

    @model_validator(mode="before")
    def validate_shape_params(cls, values):
        if not isinstance(values, dict):
            return values
        shape_type = values.get("shape_type")
        shape_params = values.get("shape_params")

        if shape_type is None:
            raise ValueError("shape_type is required")
        if shape_params is None:
            raise ValueError("shape_params are required")
        if isinstance(shape_params, TEMDBModel):
            shape_params = shape_params.model_dump()

        params_model = {
            ShapeType.CIRCLE: CircleParams,
            ShapeType.SLOT: SlotParams,
            ShapeType.RECTANGLE: RectangleParams,
            ShapeType.TRIANGLE: TriangleParams,
            ShapeType.CIRCLE_ARRAY: CircleArrayParams,
            ShapeType.POLYGON: PolygonParams,
        }.get(shape_type)
        if params_model is None:
            raise ValueError(f"Invalid shape_type: {shape_type}")
        return {**values, "shape_params": params_model(**shape_params)}


class Fiducial(Shape):
    """Represents a fiducial on a substrate."""

    name: str | None = Field(None, description="Name of the fiducial, e.g. 'origin', 'end' or 'ref'")

    through_shape: bool = Field(
        ..., description="Whether the fiducial is a through shape (e.g.,light or electrons can pass through)"
    )


class Aperture(Shape):
    """Represents a single aperture or slot on a substrate."""


class SubstrateLayoutBase(TEMDBRecord):
    """Base substrate layout fields."""

    name: str | None = Field(None, description="Human readable name of the substrate layout")
    fiducials: list[Fiducial] | None = Field(None, description="List of fiducials on the substrate")
    apertures: list[Aperture] | None = Field(
        None,
        description="Apertures in index order: apertures[i] is aperture i",
    )


class SubstrateLayoutCreate(SubstrateLayoutBase):
    """Schema for creating a substrate layout."""

    layout_id: str = Field(
        ...,
        description="Overall unique identifier for the substrate layout",
    )
    media_type: SubstrateType = Field(..., description="Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid')")
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class SubstrateLayoutUpdate(SubstrateLayoutBase):
    """Schema for updating a substrate layout."""

    media_type: SubstrateType | None = Field(None, description="Type of substrate")


class SubstrateLayoutResponse(SubstrateLayoutBase):
    """Schema for substrate layout API responses."""

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    layout_id: str = Field(
        ...,
        description="Overall unique identifier for the substrate layout",
    )
    media_type: SubstrateType = Field(..., description="Type of substrate (e.g., 'wafer', 'tape', 'stick', 'grid')")

    created_at: datetime | None = None
    updated_at: datetime | None = None
