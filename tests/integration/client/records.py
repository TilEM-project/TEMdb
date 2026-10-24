import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from temdb.client import TEMdbClient
from temdb.models import (
    AcquisitionCreate,
    DatasetCreate,
    MicroscopeCreate,
    SubstrateLayoutCreate,
    TileCreate,
)


def acquisition_payload(
    acquisition_id: str, roi_id: str, microscope_id: str, dataset_id: uuid.UUID
) -> AcquisitionCreate:
    return AcquisitionCreate(
        acquisition_id=acquisition_id,
        montage_id=f"MON-{acquisition_id}",
        acquisition_task_id="T1",
        roi_id=roi_id,
        microscope_id=microscope_id,
        dataset_id=str(dataset_id),
        hardware_settings={
            "camera_model": "c",
            "camera_serial": "1",
            "camera_bit_depth": 8,
            "media_type": "grid_disc",
        },
        acquisition_settings={
            "magnification": 1000,
            "spot_size": 1,
            "exposure_time": 1,
            "tile_size": [10, 10],
            "tile_overlap": 0.1,
            "saved_bit_depth": 8,
        },
    )


def tile_payload(raster_index: int) -> TileCreate:
    return TileCreate(
        stage_position={"x": float(raster_index), "y": 0.0},
        raster_position={"row": 0, "col": raster_index},
        image_path=f"file:///tiles/{raster_index}.tif",
        raster_index=raster_index,
    )


class Records:
    def __init__(self, client: TEMdbClient):
        self.client = client
        self._made = {}

    async def _once(self, key, make):
        if key not in self._made:
            self._made[key] = await make()
        return self._made[key]

    async def specimen(self):
        return await self._once("specimen", lambda: self.client.specimen.create(specimen_id="SP1"))

    async def block(self):
        await self.specimen()
        return await self._once("block", lambda: self.client.block.create(block_id="B1", specimen_id="SP1"))

    async def layout(self):
        return await self._once(
            "layout",
            lambda: self.client.substrate_layout.create(
                SubstrateLayoutCreate(
                    layout_id="GD-9mm-56-G1",
                    media_type="grid_disc",
                    apertures=json.loads(Path(__file__).with_name("grid_disc_56.json").read_text()),
                )
            ),
        )

    async def substrate(self):
        await self.layout()
        return await self._once(
            "substrate",
            lambda: self.client.substrate.create(media_id="M1", substrate_layout_id="GD-9mm-56-G1"),
        )

    async def cutting_session(self):
        await self.block()
        return await self._once(
            "cutting_session",
            lambda: self.client.cutting_session.create(
                cutting_session_id="CS1",
                block_id="B1",
                start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
                sectioning_device="robot",
                media_type="grid_disc",
            ),
        )

    async def section(self):
        await self.cutting_session()
        await self.substrate()
        return await self._once(
            "section",
            lambda: self.client.section.create(
                timestamp=datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
                cutting_session_id="CS1",
                media_id="M1",
                aperture_index=0,
            ),
        )

    async def roi(self):
        section = await self.section()
        return await self._once(
            "roi",
            lambda: self.client.roi.create(
                created_at=datetime(2026, 1, 1, 2, tzinfo=timezone.utc),
                section_id=section.section_id,
                payload={"vertices": [[0, 0], [10, 0], [10, 10]], "rotation_angle": 0.0},
            ),
        )

    async def task(self):
        roi = await self.roi()
        return await self._once(
            "task",
            lambda: self.client.acquisition_task.create(
                task_id="T1", specimen_id="SP1", block_id="B1", roi_id=roi.roi_id
            ),
        )

    async def microscope(self):
        return await self._once(
            "microscope",
            lambda: self.client.microscope.create(MicroscopeCreate(microscope_id="scope-1")),
        )

    async def dataset(self):
        return await self._once(
            "dataset",
            lambda: self.client.dataset.create(DatasetCreate(name="ds-1", estimated_tile_count=100)),
        )

    async def acquisition(self):
        roi = await self.roi()
        await self.task()
        microscope = await self.microscope()
        dataset = await self.dataset()
        return await self._once(
            "acquisition",
            lambda: self.client.acquisition.create(
                acquisition_payload("A1", roi.roi_id, microscope.microscope_id, dataset.dataset_id)
            ),
        )

    async def tiles(self):
        await self.acquisition()

        async def make():
            await self.client.acquisition.add_tiles_bulk("A1", [tile_payload(i) for i in range(10)])
            return await self.client.acquisition.get_all_tiles("A1")

        return await self._once("tiles", make)
