from datetime import datetime, timezone

from faker import Faker
from temdb.models import (
    AcquisitionParams,
    AcquisitionStatus,
    AcquisitionTaskStatus,
    HardwareParams,
    SectionQuality,
)
from temdb.server.documents import (
    AcquisitionDocument,
    AcquisitionTaskDocument,
    BlockDocument,
    CuttingSessionDocument,
    ROIDocument,
    SectionDocument,
    SpecimenDocument,
    SubstrateDocument,
    TileDocument,
)

fake = Faker()


def generate_specimen(**kwargs) -> SpecimenDocument:
    defaults = {
        "specimen_id": f"SPEC_{fake.unique.word()}_{int(datetime.now(timezone.utc).timestamp())}",
        "description": fake.text(max_nb_chars=150),
        "specimen_images": {fake.image_url() for _ in range(fake.random_int(min=0, max=2))},
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
        "functional_imaging_metadata": ({"source": fake.word()} if fake.boolean() else None),
    }
    defaults.update(kwargs)
    return SpecimenDocument(**defaults)


def generate_block(specimen: SpecimenDocument, **kwargs) -> BlockDocument:
    defaults = {
        "block_id": f"BLOCK_{specimen.specimen_id}_{fake.unique.random_number(digits=3)}",
        "specimen_id": specimen.specimen_id,
        "specimen_ref": specimen.id,
        "microCT_info": (
            {"resolution": fake.pyfloat(min_value=1.0, max_value=10.0, right_digits=2)} if fake.boolean() else None
        ),
    }
    defaults.update(kwargs)
    return BlockDocument(**defaults)


def generate_cutting_session(specimen: SpecimenDocument, block: BlockDocument, **kwargs) -> CuttingSessionDocument:
    defaults = {
        "cutting_session_id": f"CUT_{block.block_id}_{fake.unique.random_number(digits=4)}",
        "specimen_id": specimen.specimen_id,
        "block_id": block.block_id,
        "specimen_ref": specimen.id,
        "block_ref": block.id,
        "start_time": fake.past_datetime(start_date="-1y", tzinfo=timezone.utc),
        "end_time": (fake.past_datetime(start_date="-1y", tzinfo=timezone.utc) if fake.boolean() else None),
        "operator": fake.name(),
        "sectioning_device": fake.word().capitalize() + " Microtome",
        "media_type": "tape",
    }
    if defaults["end_time"] and defaults["end_time"] < defaults["start_time"]:
        defaults["end_time"] = defaults["start_time"] + fake.time_delta(end_datetime=datetime.now(timezone.utc))

    defaults.update(kwargs)
    return CuttingSessionDocument(**defaults)


def generate_substrate(cutting_session: CuttingSessionDocument, **kwargs) -> SubstrateDocument:
    defaults = {
        "media_id": f"MEDIA_{cutting_session.cutting_session_id}_{fake.unique.random_number(digits=4)}",
        "media_type": cutting_session.media_type,
        "substrate_id": f"SUBSTRATE_{cutting_session.cutting_session_id}",
        "description": fake.text(max_nb_chars=150),
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    }
    defaults["cutting_session_id"] = cutting_session.cutting_session_id
    defaults["block_id"] = cutting_session.block_id

    defaults.update(kwargs)
    return SubstrateDocument(**defaults)


def generate_section(
    cutting_session: CuttingSessionDocument, substrate: SubstrateDocument, section_number: int, **kwargs
) -> SectionDocument:
    defaults = {
        "section_id": f"SEC_{cutting_session.cutting_session_id}_{section_number:03d}",
        "section_number": section_number,
        "timestamp": fake.past_datetime(start_date="-1y", tzinfo=timezone.utc),
        "cutting_session_id": cutting_session.cutting_session_id,
        "block_id": cutting_session.block_id,
        "specimen_id": cutting_session.specimen_id,
        "cutting_session_ref": cutting_session.id,
        "optical_image": (
            {
                "url": fake.image_url(),
                "metadata": {"res_um": fake.pyfloat(min_value=0.5, max_value=5.0)},
            }
            if fake.boolean()
            else None
        ),
        "section_metrics": (
            {
                "quality": fake.random_element(elements=SectionQuality).value,
                "tissue_confidence_score": fake.pyfloat(min_value=0.0, max_value=1.0),
            }
            if fake.boolean()
            else None
        ),
        "media_id": f"{cutting_session.media_type.upper()}_{fake.unique.random_number(digits=5)}",
        "substrate_ref": substrate.id if substrate else None,
        "relative_position": (fake.random_int(min=1, max=10) if cutting_session.media_type == "grid" else None),
        "barcode": fake.ean13() if fake.boolean() else None,
    }
    defaults.update(kwargs)
    return SectionDocument(**defaults)


def generate_roi(
    section: SectionDocument,
    roi_number: int = 1,
    parent_roi: ROIDocument = None,
    substrate_media_id: str = "SUB001",
    **kwargs,
) -> ROIDocument:
    # Generate hierarchical roi_id string
    if parent_roi:
        roi_id = f"{parent_roi.roi_id}.ROI{roi_number:03d}"
        hierarchy_level = parent_roi.hierarchy_level + 1
    else:
        roi_id = (
            f"{section.specimen_id}.{section.block_id}.{section.cutting_session_id}"
            f".{section.section_id}.{substrate_media_id}.ROI{roi_number:03d}"
        )
        hierarchy_level = 1

    defaults = {
        "roi_id": roi_id,
        "roi_number": roi_number,
        "section_id": section.section_id,
        "block_id": section.block_id,
        "specimen_id": section.specimen_id,
        "substrate_media_id": substrate_media_id,
        "hierarchy_level": hierarchy_level,
        "section_ref": section.id,
        "parent_roi_ref": parent_roi.id if parent_roi else None,
        "aperture_image": fake.file_path(extension="png") if fake.boolean() else None,
        "optical_pixel_size": (fake.pyfloat(min_value=100.0, max_value=1000.0) if fake.boolean() else None),
        "updated_at": datetime.now(timezone.utc),
        "section_number": section.section_number,
    }
    defaults.update(kwargs)
    return ROIDocument(**defaults)


def generate_acquisition_task(
    specimen: SpecimenDocument, block: BlockDocument, roi: ROIDocument, **kwargs
) -> AcquisitionTaskDocument:
    defaults = {
        "task_id": f"TASK_{roi.roi_id}_{fake.unique.random_number(digits=3)}",
        "specimen_id": specimen.specimen_id,
        "block_id": block.block_id,
        "roi_id": roi.roi_id,
        "specimen_ref": specimen.id,
        "block_ref": block.id,
        "roi_ref": roi.id,
        "tags": [fake.word() for _ in range(fake.random_int(min=0, max=3))],
        "metadata": ({"priority": fake.random_int(min=1, max=10)} if fake.boolean() else {}),
        "task_type": "standard_acquisition",
        "version": 1,
        "status": fake.random_element(elements=AcquisitionTaskStatus).value,
        "created_at": fake.past_datetime(start_date="-30d", tzinfo=timezone.utc),
        "updated_at": None,
        "started_at": None,
        "completed_at": None,
        "error_message": None,
    }
    defaults.update(kwargs)
    return AcquisitionTaskDocument(**defaults)


def generate_acquisition(
    specimen: SpecimenDocument, roi: ROIDocument, task: AcquisitionTaskDocument, **kwargs
) -> AcquisitionDocument:
    defaults = {
        "acquisition_id": f"ACQ_{task.task_id}_{fake.unique.random_number(digits=4)}",
        "montage_id": f"MONT_{task.task_id}_{fake.unique.random_number(digits=4)}",
        "specimen_id": specimen.specimen_id,
        "roi_id": roi.roi_id,
        "acquisition_task_id": task.task_id,
        "specimen_ref": specimen.id,
        "roi_ref": roi.id,
        "acquisition_task_ref": task.id,
        "hardware_settings": HardwareParams(
            scope_id=f"SEM_{fake.random_int(min=1, max=3)}",
            camera_model=fake.random_element(elements=["CamA", "CamB", "CamX"]),
            camera_serial=fake.uuid4(),
            camera_bit_depth=16,
            media_type=fake.random_element(elements=["tape", "grid"]),
        ),
        "acquisition_settings": AcquisitionParams(
            magnification=fake.random_element(elements=[500, 1000, 2000, 5000]),
            spot_size=fake.random_int(min=1, max=5),
            exposure_time=fake.random_int(min=50, max=500),
            tile_size=[4096, 4096],
            tile_overlap=fake.pyfloat(min_value=0.05, max_value=0.2, right_digits=2),
            saved_bit_depth=8,
        ),
        "calibration_info": None,
        "status": fake.random_element(elements=AcquisitionStatus).value,
        "tilt_angle": fake.pyfloat(min_value=-5, max_value=5, right_digits=1),
        "lens_correction": fake.boolean(),
        "start_time": fake.past_datetime(start_date="-7d", tzinfo=timezone.utc),
        "end_time": None,
        "storage_locations": [],
        "montage_set_name": f"Set_{roi.roi_id}" if fake.boolean() else None,
        "sub_region": None,
        "replaces_acquisition_id": None,
    }
    defaults.update(kwargs)
    return AcquisitionDocument(**defaults)


def generate_tile(acquisition: AcquisitionDocument, raster_index: int, **kwargs) -> TileDocument:
    defaults = {
        "tile_id": f"TILE_{acquisition.acquisition_id}_{raster_index:04d}",
        "acquisition_id": acquisition.acquisition_id,
        "acquisition_ref": acquisition.id,
        "raster_index": raster_index,
        "stage_position": {"x": fake.pyfloat(), "y": fake.pyfloat()},
        "raster_position": {"row": raster_index // 10, "col": raster_index % 10},
        "focus_score": fake.pyfloat(min_value=0.1, max_value=1.0),
        "min_value": fake.pyfloat(min_value=0, max_value=5000),
        "max_value": fake.pyfloat(min_value=20000, max_value=65535),
        "mean_value": fake.pyfloat(min_value=5000, max_value=40000),
        "std_value": fake.pyfloat(min_value=1000, max_value=10000),
        "image_path": f"/path/to/acq/{acquisition.acquisition_id}/tile_{raster_index:04d}.tif",
        "matcher": None,
        "supertile_id": None,
        "supertile_raster_position": None,
    }
    defaults.update(kwargs)
    return TileDocument(**defaults)
