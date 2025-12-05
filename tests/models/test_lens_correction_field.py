from temdb.models import AcquisitionCreate


def test_acquisition_with_lens_correction_reference():
    """Test that acquisitions can reference a lens correction acquisition."""
    acq = AcquisitionCreate(
        acquisition_id="ACQ001",
        montage_id="MONTAGE001",
        roi_id="ROI001",
        acquisition_task_id="TASK001",
        hardware_settings={
            "scope_id": "TEM1",
            "camera_model": "Test",
            "camera_serial": "123",
            "camera_bit_depth": 16,
            "media_type": "tape",
        },
        acquisition_settings={
            "magnification": 2000,
            "spot_size": 3,
            "exposure_time": 100,
            "tile_size": [4096, 4096],
            "tile_overlap": 0.1,
            "saved_bit_depth": 8,
        },
        tilt_angle=0.0,
        lens_correction=False,
        lens_correction_acquisition_id="LC_ACQ001",
    )
    assert acq.lens_correction_acquisition_id == "LC_ACQ001"


def test_lens_correction_acquisition_has_no_reference():
    """Lens correction acquisitions should not reference another LC."""
    lc_acq = AcquisitionCreate(
        acquisition_id="LC_ACQ001",
        montage_id="LC_MONTAGE001",
        roi_id="ROI001",
        acquisition_task_id="TASK001",
        hardware_settings={
            "scope_id": "TEM1",
            "camera_model": "Test",
            "camera_serial": "123",
            "camera_bit_depth": 16,
            "media_type": "tape",
        },
        acquisition_settings={
            "magnification": 2000,
            "spot_size": 3,
            "exposure_time": 100,
            "tile_size": [4096, 4096],
            "tile_overlap": 0.1,
            "saved_bit_depth": 8,
        },
        tilt_angle=0.0,
        lens_correction=True,
        lens_correction_acquisition_id=None,
    )
    assert lc_acq.lens_correction is True
    assert lc_acq.lens_correction_acquisition_id is None
