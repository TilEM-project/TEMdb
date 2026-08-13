import uuid

import pytest

from temdb.server.sqlmodels.tile_partition import (
    SIZE_CLASS_CEILING,
    SIZE_CLASS_MODULUS,
    lock_key,
    partition_name,
    resolve_modulus,
    resolve_size_class,
)


def test_size_class_modulus_values():
    assert SIZE_CLASS_MODULUS == {
        "small": 4,
        "medium": 32,
        "large": 256,
        "xlarge": 1024,
    }


@pytest.mark.parametrize(
    "size_class,expected",
    [
        ("small", 4),
        ("medium", 32),
        ("large", 256),
        ("xlarge", 1024),
    ],
)
def test_resolve_modulus_known(size_class, expected):
    assert resolve_modulus(size_class) == expected


def test_resolve_modulus_unknown_raises():
    with pytest.raises(ValueError):
        resolve_modulus("gigantic")


def test_partition_name_is_deterministic_hex():
    ds = uuid.UUID("018f9c2a-7b3d-7e4f-8a1b-2c3d4e5f6a7b")
    assert partition_name(ds) == f"tile_d_{ds.hex}"


def test_lock_key_is_stable_signed_64bit():
    ds = uuid.UUID("018f9c2a-7b3d-7e4f-8a1b-2c3d4e5f6a7b")
    key = lock_key(ds)
    assert isinstance(key, int)
    assert -(2**63) <= key < 2**63
    assert lock_key(ds) == key  # deterministic


def test_size_class_ceiling_values():
    assert SIZE_CLASS_CEILING == {
        "small": 100_000_000,
        "medium": 1_000_000_000,
        "large": 10_000_000_000,
    }


@pytest.mark.parametrize(
    "count,expected",
    [
        (0, "small"),
        (100_000_000, "small"),
        (100_000_001, "medium"),
        (1_000_000_000, "medium"),
        (1_000_000_001, "large"),
        (10_000_000_000, "large"),
        (10_000_000_001, "xlarge"),
        (50_000_000_000, "xlarge"),
    ],
)
def test_resolve_size_class(count, expected):
    assert resolve_size_class(count) == expected


def test_resolve_size_class_negative_raises():
    with pytest.raises(ValueError):
        resolve_size_class(-1)
