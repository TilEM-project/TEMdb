import uuid
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from fastapi.routing import APIRoute
from starlette.routing import Match

from temdb.client import TEMdbClient
from temdb.models import (
    AcquisitionCreate,
    DatasetCreate,
    MicroscopeCreate,
    SubstrateLayoutCreate,
    TileCreate,
)
from temdb.server.dependencies import get_db_manager


class RecordingTransport(httpx.AsyncBaseTransport):
    def __init__(self, app: FastAPI):
        self._inner = httpx.ASGITransport(app=app)
        self.requests: list[tuple[str, str]] = []
        self.gzipped_requests: list[tuple[str, str]] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append((request.method, request.url.path))
        if request.headers.get("content-encoding") == "gzip":
            self.gzipped_requests.append((request.method, request.url.path))
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()


def unmatched_requests(app: FastAPI, requests: list[tuple[str, str]]) -> list[tuple[str, str]]:
    routes = [route for route in app.routes if isinstance(route, APIRoute)]
    unmatched = []
    for method, path in requests:
        scope = {"type": "http", "method": method, "path": path, "root_path": ""}
        if not any(route.matches(scope)[0] is Match.FULL for route in routes):
            unmatched.append((method, path))
    return unmatched


class LiveServer:
    def __init__(self, app: FastAPI, db_manager):
        self.app = app
        self.app.dependency_overrides[get_db_manager] = lambda: db_manager
        self.transport = RecordingTransport(self.app)
        self.client = TEMdbClient("http://test", transport=self.transport)

    def unmatched_requests(self) -> list[tuple[str, str]]:
        return unmatched_requests(self.app, self.transport.requests)


def acquisition_payload(
    acquisition_id: str, roi_id: str, microscope_id: uuid.UUID, dataset_id: uuid.UUID
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
            "media_type": "tape",
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


class Seed:
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
            lambda: self.client.substrate_layout.create(SubstrateLayoutCreate(layout_id="L1", media_type="tape")),
        )

    async def substrate(self):
        await self.layout()
        return await self._once(
            "substrate",
            lambda: self.client.substrate.create(media_id="M1", substrate_layout_id="L1"),
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
                media_type="tape",
            ),
        )

    async def section(self):
        await self.cutting_session()
        await self.substrate()
        return await self._once(
            "section",
            lambda: self.client.section.create(
                section_number=1, cutting_session_id="CS1", media_id="M1", barcode="BC1"
            ),
        )

    async def roi(self):
        section = await self.section()
        return await self._once(
            "roi",
            lambda: self.client.roi.create(
                roi_number=1,
                section_id=section.section_id,
                specimen_id="SP1",
                block_id="B1",
                substrate_media_id="M1",
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
            lambda: self.client.microscope.create(MicroscopeCreate(label="scope-1")),
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
