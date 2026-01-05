from datetime import datetime

import pytest
from pydantic import ValidationError
from temdb.models import (
    AcquisitionCreate,
    AcquisitionParams,
    AcquisitionResponse,
    AcquisitionStatus,
    AcquisitionUpdate,
    Calibration,
    HardwareParams,
    StorageLocation,
    StorageLocationCreate,
)


class TestHardwareParams:
    def test_valid_hardware_params(self):
        params = HardwareParams(
            scope_id="SCOPE001",
            camera_model="Test Camera",
            camera_serial="12345",
            camera_bit_depth=16,
            media_type="tape",
        )
        assert params.scope_id == "SCOPE001"
        assert params.camera_model == "Test Camera"
        assert params.camera_bit_depth == 16

    def test_all_fields_required(self):
        with pytest.raises(ValidationError):
            HardwareParams()

    def test_extra_fields_allowed(self):
        params = HardwareParams(
            scope_id="SCOPE001",
            camera_model="Test Camera",
            camera_serial="12345",
            camera_bit_depth=16,
            media_type="tape",
            custom_field="value",
        )
        assert params.custom_field == "value"


class TestAcquisitionParams:
    def test_valid_acquisition_params(self):
        params = AcquisitionParams(
            magnification=1000,
            spot_size=2,
            exposure_time=100,
            tile_size=[4096, 4096],
            tile_overlap=0.1,
            saved_bit_depth=8,
        )
        assert params.magnification == 1000
        assert params.tile_size == [4096, 4096]
        assert params.tile_overlap == 0.1

    def test_all_fields_required(self):
        with pytest.raises(ValidationError):
            AcquisitionParams()


class TestCalibration:
    def test_valid_calibration(self):
        cal = Calibration(
            pixel_size=4.0,
            rotation_angle=0.5,
        )
        assert cal.pixel_size == 4.0
        assert cal.rotation_angle == 0.5
        assert cal.lens_model is None

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            Calibration()


class TestStorageLocation:
    def test_valid_storage_location(self):
        loc = StorageLocation(
            location_type="local",
            base_path="/data/acquisitions/ACQ001",
            is_current=True,
            date_added=datetime.now(),
            metadata={"server": "storage1"},
        )
        assert loc.location_type == "local"
        assert loc.is_current is True


class TestStorageLocationCreate:
    def test_valid_storage_location_create(self):
        loc = StorageLocationCreate(
            location_type="s3",
            base_path="s3://bucket/path",
        )
        assert loc.location_type == "s3"
        assert loc.metadata == {}


class TestAcquisitionCreate:
    def test_valid_acquisition_create(self):
        acq = AcquisitionCreate(
            acquisition_id="ACQ001",
            montage_id="MONTAGE001",
            roi_id="ROI001",
            acquisition_task_id="TASK001",
            hardware_settings=HardwareParams(
                scope_id="SCOPE001",
                camera_model="Test Camera",
                camera_serial="12345",
                camera_bit_depth=16,
                media_type="tape",
            ),
            acquisition_settings=AcquisitionParams(
                magnification=1000,
                spot_size=2,
                exposure_time=100,
                tile_size=[4096, 4096],
                tile_overlap=0.1,
                saved_bit_depth=8,
            ),
            tilt_angle=0.0,
            lens_correction=False,
        )
        assert acq.acquisition_id == "ACQ001"
        assert acq.status == AcquisitionStatus.IMAGING

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            AcquisitionCreate()

    def test_default_status(self):
        acq = AcquisitionCreate(
            acquisition_id="ACQ001",
            montage_id="MONTAGE001",
            roi_id="ROI001",
            acquisition_task_id="TASK001",
            hardware_settings=HardwareParams(
                scope_id="SCOPE001",
                camera_model="Test Camera",
                camera_serial="12345",
                camera_bit_depth=16,
                media_type="tape",
            ),
            acquisition_settings=AcquisitionParams(
                magnification=1000,
                spot_size=2,
                exposure_time=100,
                tile_size=[4096, 4096],
                tile_overlap=0.1,
                saved_bit_depth=8,
            ),
            tilt_angle=0.0,
            lens_correction=False,
        )
        assert acq.status == AcquisitionStatus.IMAGING


class TestAcquisitionUpdate:
    def test_all_fields_optional(self):
        update = AcquisitionUpdate()
        assert update.status is None
        assert update.end_time is None

    def test_partial_update(self):
        update = AcquisitionUpdate(
            status=AcquisitionStatus.ACQUIRED,
            end_time=datetime.now(),
        )
        assert update.status == AcquisitionStatus.ACQUIRED


class TestAcquisitionResponse:
    def test_valid_response(self):
        response = AcquisitionResponse(
            acquisition_id="ACQ001",
            montage_id="MONTAGE001",
            specimen_id="SPEC001",
            roi_id="ROI001",
            acquisition_task_id="TASK001",
            hardware_settings=HardwareParams(
                scope_id="SCOPE001",
                camera_model="Test Camera",
                camera_serial="12345",
                camera_bit_depth=16,
                media_type="tape",
            ),
            acquisition_settings=AcquisitionParams(
                magnification=1000,
                spot_size=2,
                exposure_time=100,
                tile_size=[4096, 4096],
                tile_overlap=0.1,
                saved_bit_depth=8,
            ),
            status=AcquisitionStatus.ACQUIRED,
            start_time=datetime.now(),
        )
        assert response.acquisition_id == "ACQ001"
        assert response.specimen_id == "SPEC001"
