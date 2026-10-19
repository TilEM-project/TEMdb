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
    with pytest.raises(ValidationError) as rejected:
        Aperture(
            shape_type="circle",
            shape_params={"width": 1.0, "height": 2.0},
            centroid=(0.0, 0.0),
        )

    assert [(error["loc"], error["msg"]) for error in rejected.value.errors()] == [
        (("shape_params", "diameter"), "Field required"),
        (("shape_params", "width"), "Extra inputs are not permitted"),
        (("shape_params", "height"), "Extra inputs are not permitted"),
    ]


@pytest.mark.parametrize("shape_params", [[1.0, 2.0], 3])
def test_shape_params_must_be_an_object(shape_params):
    with pytest.raises(ValidationError) as rejected:
        Aperture(shape_type="slot", shape_params=shape_params, centroid=(0.0, 0.0))

    assert [(error["loc"], error["msg"]) for error in rejected.value.errors()] == [
        (("shape_params",), "Input should be a valid dictionary or instance of SlotParams"),
    ]


def test_shape_type_must_be_a_known_shape():
    with pytest.raises(ValidationError) as rejected:
        Aperture(shape_type="hexagon", shape_params={"diameter": 1.0}, centroid=(0.0, 0.0))

    assert [(error["loc"], error["type"]) for error in rejected.value.errors()] == [
        (("shape_type",), "enum"),
        (("shape_params",), "value_error"),
    ]


def test_shape_type_and_params_are_required():
    with pytest.raises(ValidationError) as rejected:
        Aperture(centroid=(0.0, 0.0))

    assert [(error["loc"], error["type"]) for error in rejected.value.errors()] == [
        (("shape_type",), "missing"),
        (("shape_params",), "missing"),
    ]


def test_polygon_needs_three_vertices():
    with pytest.raises(ValidationError):
        Aperture(shape_type="polygon", shape_params={"vertices": [(0.0, 0.0), (1.0, 0.0)]}, centroid=(0.0, 0.0))
