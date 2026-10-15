import pytest
from pydantic import ValidationError

from temdb.models import (
    Aperture,
    Fiducial,
    ShapeType,
    SubstrateLayoutCreate,
    SubstrateLayoutUpdate,
)


def test_aperture_parses_parameters_for_its_shape():
    aperture = Aperture(
        shape_type="circle",
        shape_params={"diameter": 1.0},
        centroid=(1.0, 2.0),
    )

    assert aperture.shape_type is ShapeType.CIRCLE
    assert aperture.shape_params.diameter == 1.0
    assert aperture.centroid == (1.0, 2.0)


def test_fiducial_requires_through_shape():
    with pytest.raises(ValidationError, match="through_shape"):
        Fiducial(
            shape_type="circle",
            shape_params={"diameter": 0.4},
            centroid=(0.0, 0.0),
        )


def test_layout_create_accepts_ordered_apertures_and_fiducials():
    layout = SubstrateLayoutCreate(
        layout_id="LAYOUT001",
        name="Test layout",
        media_type="wafer",
        apertures=[
            {
                "shape_type": "slot",
                "shape_params": {"width": 0.1, "height": 0.8, "angle": 30},
                "centroid": (1.0, 2.0),
            },
            {
                "shape_type": "polygon",
                "shape_params": {"vertices": [(-1.0, -1.0), (1.0, -1.0), (0.0, 1.0)]},
                "centroid": (5.0, 2.0),
            },
        ],
        fiducials=[
            {
                "shape_type": "circle",
                "shape_params": {"diameter": 0.4},
                "centroid": (0.0, 0.0),
                "through_shape": True,
            }
        ],
    )

    assert layout.apertures[0].shape_params.width == 0.1
    assert layout.apertures[1].shape_params.vertices[2] == (0.0, 1.0)
    assert layout.fiducials[0].through_shape is True


def test_layout_requires_identifier_and_media_type():
    with pytest.raises(ValidationError):
        SubstrateLayoutCreate(layout_id="LAYOUT001")


def test_layout_update_fields_are_optional():
    assert SubstrateLayoutUpdate().model_dump(exclude_unset=True) == {}


def test_shape_rejects_params_for_a_different_shape():
    with pytest.raises(ValidationError):
        Aperture(
            shape_type="circle",
            shape_params={"width": 1.0, "height": 2.0},
            centroid=(0.0, 0.0),
        )


def test_polygon_needs_three_vertices():
    with pytest.raises(ValidationError):
        Aperture(shape_type="polygon", shape_params={"vertices": [(0.0, 0.0), (1.0, 0.0)]}, centroid=(0.0, 0.0))
