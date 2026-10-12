import gzip
import json
import logging
from typing import Any, cast

import httpx
from pydantic_core import to_jsonable_python
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import TEMdbClientError, TEMdbServerError
from .resources.acquisition import AcquisitionResource
from .resources.block import BlockResource
from .resources.cutting_session import CuttingSessionResource
from .resources.dataset import DatasetResource
from .resources.lens_correction import LensCorrectionResource
from .resources.microscope import MicroscopeResource
from .resources.roi import ROIResource
from .resources.section import SectionResource
from .resources.specimen import SpecimenResource
from .resources.substrate import SubstrateResource
from .resources.task import AcquisitionTaskResource


class TEMdbClient:
    def __init__(
        self,
        base_url: str,
        api_version: str = "v2",
        api_key: str | None = None,
        timeout: float = 30.0,
        debug: bool = False,
    ):
        self.raw_base_url = base_url
        self.api_version = api_version
        self.api_url = f"{base_url}/api/{api_version}"
        self.api_key = api_key
        self.timeout = timeout

        self.logger = logging.getLogger("temdb_client.async")
        level = logging.DEBUG if debug else logging.INFO
        self.logger.setLevel(level)

        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        self._http_client = httpx.AsyncClient(
            base_url=self.api_url,
            headers=headers,
            timeout=timeout,
        )

        self.logger.info(f"Async TEMdb client initialized: {base_url} (API v{api_version})")

        self._specimen = SpecimenResource(self._async_request, self.api_url)
        self._block = BlockResource(self._async_request, self.api_url)
        self._cutting_session = CuttingSessionResource(self._async_request, self.api_url)
        self._substrate = SubstrateResource(self._async_request, self.api_url)
        self._acquisition_task = AcquisitionTaskResource(self._async_request, self.api_url)
        self._roi = ROIResource(self._async_request, self.api_url)
        self._acquisition = AcquisitionResource(self._async_request, self.api_url)
        self._dataset = DatasetResource(self._async_request, self.api_url)
        self._section = SectionResource(self._async_request, self.api_url)
        self._microscope = MicroscopeResource(self._async_request, self.api_url)
        self._lens_correction = LensCorrectionResource(self._async_request, self.api_url)

    @property
    def specimen(self) -> SpecimenResource:
        return self._specimen

    @property
    def block(self) -> BlockResource:
        return self._block

    @property
    def cutting_session(self) -> CuttingSessionResource:
        return self._cutting_session

    @property
    def substrate(self) -> SubstrateResource:
        return self._substrate

    @property
    def acquisition_task(self) -> AcquisitionTaskResource:
        return self._acquisition_task

    @property
    def roi(self) -> ROIResource:
        return self._roi

    @property
    def acquisition(self) -> AcquisitionResource:
        return self._acquisition

    @property
    def dataset(self) -> DatasetResource:
        return self._dataset

    @property
    def section(self) -> SectionResource:
        return self._section

    @property
    def microscope(self) -> MicroscopeResource:
        return self._microscope

    @property
    def lens_correction(self) -> LensCorrectionResource:
        return self._lens_correction

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def _async_request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any] | list[Any]:
        self.logger.debug(f"Async Request: {method} {endpoint}")
        try:
            if "json" in kwargs and method.upper() in ("POST", "PATCH", "PUT"):
                body = json.dumps(kwargs.pop("json"), default=to_jsonable_python).encode("utf-8")
                if len(body) > 1000:
                    self.logger.debug(f"Compressing request body: {len(body)} bytes")
                    kwargs["content"] = gzip.compress(body)
                    kwargs["headers"] = {
                        **kwargs.get("headers", {}),
                        "Content-Encoding": "gzip",
                        "Content-Type": "application/json",
                    }
                else:
                    kwargs["content"] = body
                    kwargs["headers"] = {
                        **kwargs.get("headers", {}),
                        "Content-Type": "application/json",
                    }

            response = await self._http_client.request(method, endpoint, **kwargs)
            response.raise_for_status()
            if response.status_code == 204:
                return {}
            return response.json()
        except httpx.HTTPStatusError as e:
            self.logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise TEMdbServerError.from_httpx_status_error(e) from e
        except httpx.RequestError as e:
            self.logger.error(f"Request failed: {str(e)}")
            raise TEMdbClientError(f"Request failed: {str(e)}") from e
        except Exception as e:
            self.logger.exception(f"An unexpected error occurred during request to {endpoint}")
            raise TEMdbClientError(f"Unexpected error: {str(e)}") from e

    async def health_check(self) -> dict[str, Any]:
        """Check if the API is available."""
        try:
            result = await self._async_request("GET", "/health")
            self.logger.info(f"Async Health check: {result.get('status', 'unknown')}")
            return cast(dict[str, Any], result)
        except Exception as e:
            self.logger.error(f"Async Health check failed: {str(e)}")
            raise

    async def get_api_info(self) -> dict[str, Any]:
        """Get API information."""
        result = await self._async_request("GET", "/")
        return cast(dict[str, Any], result)

    async def close(self) -> None:
        self.logger.info("Closing async TEMdb client")
        await self._http_client.aclose()

    async def __aenter__(self) -> "TEMdbClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
