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
        shape_params={"radius": 0.5},
        centroid=(1.0, 2.0),
    )

    assert aperture.shape_type is ShapeType.CIRCLE
    assert aperture.shape_params.radius == 0.5
    assert aperture.centroid == (1.0, 2.0)


def test_fiducial_requires_through_shape():
    with pytest.raises(ValidationError, match="through_shape"):
        Fiducial(
            shape_type="circle",
            shape_params={"radius": 0.2},
            centroid=(0.0, 0.0),
        )


def test_layout_create_accepts_indexed_apertures_and_fiducials():
    layout = SubstrateLayoutCreate(
        layout_id="LAYOUT001",
        name="Test layout",
        media_type="wafer",
        apertures={
            4: {
                "shape_type": "slot",
                "shape_params": {"width": 0.1, "height": 0.8, "angle": 30},
                "centroid": (1.0, 2.0),
            }
        },
        fiducials=[
            {
                "shape_type": "circle",
                "shape_params": {"radius": 0.2},
                "centroid": (0.0, 0.0),
                "through_shape": True,
            }
        ],
    )

    assert layout.apertures[4].shape_params.width == 0.1
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
