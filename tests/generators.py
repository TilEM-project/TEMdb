from faker import Faker
from bson import ObjectId

from temdb.models.v2.specimen import Specimen
from temdb.models.v2.acquisition import Acquisition
from temdb.models.v2.tile import Tile
from temdb.models.v2.roi import ROI
from temdb.models.v2.imaging_session import ImagingSession
from temdb.models.v2.enum_schemas import (
    AcquisitionStatus,
    MediaType,
    ImagingSessionStatus,
    SectionQuality,
)
from temdb.models.v2.block import Block
from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.section import Section

fake = Faker()


def generate_specimen() -> Specimen:
    return Specimen(
        specimen_id=fake.word(),
        description=fake.text(max_nb_chars=200),
        specimen_images=[fake.image_url() for _ in range(3)],
        created_at=fake.date_time_this_year(),
        updated_at=fake.date_time_this_year(),
        functional_imaging_metadata={},
    )


def generate_block(specimen_id: ObjectId) -> Block:
    return Block(
        block_id=fake.word(),
        microCT_info={"resolution": fake.pyfloat(min_value=1.0, max_value=10.0)},
        specimen_id=specimen_id,
    )


def generate_cutting_session(
    specimen_id: ObjectId, block_id: ObjectId
) -> CuttingSession:
    return CuttingSession(
        cutting_session_id=fake.uuid4(),
        start_time=fake.date_time_this_year(),
        end_time=fake.date_time_this_year(),
        operator=fake.name(),
        sectioning_device=fake.word(),
        media_type=fake.random_element(elements=MediaType),
        specimen_id=specimen_id,
        block_id=block_id,
    )


def generate_section(cutting_session_id: ObjectId) -> Section:
    return Section(
        section_id=fake.uuid4(),
        section_number=fake.random_int(min=1, max=100),
        optical_image={
            "url": fake.image_url(),
            "metadata": {"resolution": fake.pyfloat(min_value=1.0, max_value=10.0)},
        },
        section_metrics={
            "sectioning_metadata": {
                "angle": fake.pyfloat(min_value=0.0, max_value=45.0)
            },
            "quality": fake.random_element(elements=SectionQuality),
            "tissue_confidence_score": fake.pyfloat(min_value=0.0, max_value=1.0),
        },
        media_type=fake.random_element(elements=MediaType),
        media_id=fake.uuid4(),
        relative_position=fake.random_int(min=1, max=100),
        barcode=fake.ean13() if fake.boolean() else None,
        cutting_session_id=cutting_session_id,
    )


def generate_roi(section_number: int) -> ROI:
    return ROI(
        roi_id=fake.random_int(min=1, max=100),
        aperture_width_height=[fake.random_int(min=1, max=100) for _ in range(2)],
        aperture_centroid=[fake.pyfloat(), fake.pyfloat()],
        aperture_bounding_box=[fake.pyfloat() for _ in range(4)],
        optical_nm_per_pixel=fake.pyfloat(),
        scale_y=fake.pyfloat(),
        barcode=fake.ean13() if fake.boolean() else None,
        rois=[],
        bucket=fake.word(),
        aperture_image=fake.file_path(),
        roi_mask=fake.file_path(),
        roi_mask_bucket=fake.word(),
        corners={
            "top_left": [fake.pyfloat(), fake.pyfloat()],
            "top_right": [fake.pyfloat(), fake.pyfloat()],
            "bottom_left": [fake.pyfloat(), fake.pyfloat()],
            "bottom_right": [fake.pyfloat(), fake.pyfloat()],
        },
        corners_perpendicular={
            "top_left": [fake.pyfloat(), fake.pyfloat()],
            "top_right": [fake.pyfloat(), fake.pyfloat()],
            "bottom_left": [fake.pyfloat(), fake.pyfloat()],
            "bottom_right": [fake.pyfloat(), fake.pyfloat()],
        },
        rule=fake.word(),
        edits=[fake.word() for _ in range(3)],
        updated_at=str(fake.date_time_this_year()),
        auto_roi=fake.boolean(),
        section_number=section_number,
        parent_roi_id=None,
        roi_parameters={},
    )


def generate_imaging_session(
    specimen_id: ObjectId, block_id: ObjectId, roi_ids: list[ObjectId]
) -> ImagingSession:
    return ImagingSession(
        session_id=f"{specimen_id}_{block_id}_{fake.random_int(min=1, max=100)}",
        specimen_id=specimen_id,
        block=block_id,
        media_type=fake.random_element(elements=MediaType),
        media_id=fake.uuid4(),
        start_time=fake.date_time_this_year(),
        end_time=fake.date_time_this_year(),
        status=fake.random_element(elements=ImagingSessionStatus),
        rois=[roi_ids],
    )


def generate_acquisition(
    specimen_id: ObjectId, roi_id: ObjectId, imaging_session_id: ObjectId
) -> Acquisition:
    return Acquisition(
        metadata_version=fake.pystr(min_chars=4, max_chars=8),
        specimen_id=specimen_id,
        montage_id=fake.uuid4(),
        acquisition_id=fake.uuid4(),
        roi_id=roi_id,
        imaging_session_id=imaging_session_id,
        hardware_settings={
            "scope_id": fake.pystr(),
            "camera_model": fake.pystr(),
            "camera_serial": fake.uuid4(),
            "bit_depth": fake.random_int(min=8, max=16),
            "media_type": "tape",
        },
        acquisition_settings={
            "magnification": fake.random_int(min=1, max=100),
            "spot_size": fake.random_int(min=1, max=10),
            "exposure_time": fake.random_int(min=1, max=1000),
            "tile_size": [
                fake.random_int(min=512, max=2048),
                fake.random_int(min=512, max=2048),
            ],
            "tile_overlap": fake.pyfloat(min_value=0.0, max_value=0.5),
        },
        calibration_info={
            "pixel_size": fake.pyfloat(),
            "stig_angle": fake.pyfloat(),
            "lens_model": {
                "id": fake.random_int(),
                "type": fake.pystr(),
                "class_name": fake.pystr(),
                "data_string": fake.pystr(),
            },
            "aperture_centroid": [fake.pyfloat(), fake.pyfloat()],
        },
        status=fake.random_element(elements=AcquisitionStatus),
        tilt_angle=fake.pyfloat(min_value=-15, max_value=15),
        lens_correction=fake.boolean(),
        start_time=fake.date_time_this_year(),
        tile_ids=[],
        montage_set_name=fake.word(),
        sub_region={
            "x": fake.random_int(min=0, max=100),
            "y": fake.random_int(min=0, max=100),
        },
        replaces_acquisition_id=None,
    )


def generate_tile(raster_index, acquisition_id: ObjectId) -> Tile:
    return Tile(
        tile_id=fake.uuid4(),
        acquisition_id=acquisition_id,
        raster_index=raster_index,
        stage_position={
            "x": fake.pyfloat(min_value=0, max_value=1000),
            "y": fake.pyfloat(min_value=0, max_value=1000),
        },
        raster_position={
            "row": fake.random_int(min=0, max=100),
            "col": fake.random_int(min=0, max=100),
        },
        focus_score=fake.pyfloat(min_value=0, max_value=100),
        min_value=fake.pyfloat(min_value=0, max_value=100),
        max_value=fake.pyfloat(min_value=0, max_value=100),
        mean_value=fake.pyfloat(min_value=0, max_value=100),
        std_value=fake.pyfloat(min_value=0, max_value=100),
        image_path=fake.file_path(),
        matcher=[
            {
                "row": fake.random_int(min=0, max=100),
                "col": fake.random_int(min=0, max=100),
                "dX": fake.pyfloat(),
                "dY": fake.pyfloat(),
                "dXsd": fake.pyfloat(),
                "dYsd": fake.pyfloat(),
                "distance": fake.pyfloat(),
                "rotation": fake.pyfloat(),
                "match_quality": fake.pyfloat(),
                "position": fake.random_int(min=0, max=100),
                "pX": [fake.pyfloat() for _ in range(4)],
                "pY": [fake.pyfloat() for _ in range(4)],
                "qX": [fake.pyfloat() for _ in range(4)],
                "qY": [fake.pyfloat() for _ in range(4)],
            }
        ],
        supertile_id=fake.uuid4(),
        supertile_raster_position={
            "row": fake.random_int(min=0, max=10),
            "col": fake.random_int(min=0, max=10),
        },
    )
