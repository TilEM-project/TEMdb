import pytest
from pydantic import ValidationError

from temdb.models import DatasetCreate, DatasetUpdate


def test_dataset_create_defaults():
    model = DatasetCreate(name="mouse42_left_hemi")
    assert model.name == "mouse42_left_hemi"
    assert model.size_class is None


def test_dataset_create_rejects_bad_size_class():
    with pytest.raises(ValidationError):
        DatasetCreate(name="x", size_class="gigantic")


def test_dataset_update_is_partial():
    model = DatasetUpdate(status="archived")
    assert model.model_dump(exclude_unset=True) == {"status": "archived"}


def test_dataset_create_size_class_optional_and_estimate_field():
    model = DatasetCreate(name="x", estimated_tile_count=2_000_000_000)
    assert model.size_class is None
    assert model.estimated_tile_count == 2_000_000_000


def test_dataset_create_neither_size_nor_estimate_is_allowed_by_model():
    # The model permits both-None; the SERVER enforces the 'must set one' rule.
    model = DatasetCreate(name="x")
    assert model.size_class is None
    assert model.estimated_tile_count is None
