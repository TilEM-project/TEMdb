import asyncio
import gzip
import json
import logging
from typing import Any, cast

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import NotFoundError, TEMdbClientError
from .resources.acquisition import AcquisitionResource
from .resources.block import BlockResource
from .resources.cutting_session import CuttingSessionResource
from .resources.roi import ROIResource
from .resources.section import SectionResource
from .resources.specimen import SpecimenResource
from .resources.substrate import SubstrateResource
from .resources.sync_wrappers import (
    SyncAcquisitionResourceWrapper,
    SyncAcquisitionTaskResourceWrapper,
    SyncBlockResourceWrapper,
    SyncCuttingSessionResourceWrapper,
    SyncROIResourceWrapper,
    SyncSectionResourceWrapper,
    SyncSpecimenResourceWrapper,
    SyncSubstrateResourceWrapper,
)
from .resources.task import AcquisitionTaskResource


class AsyncTEMdbClient:
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
        self._section = SectionResource(self._async_request, self.api_url)

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
    def section(self) -> SectionResource:
        return self._section

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(httpx.RequestError),
    )
    async def _async_request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any] | list[Any]:
        self.logger.debug(f"Async Request: {method} {endpoint}")
        try:
            if "json" in kwargs and method.upper() in ("POST", "PATCH", "PUT"):
                body = json.dumps(kwargs.pop("json")).encode("utf-8")
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
            if e.response.status_code == 404:
                raise NotFoundError(f"Resource not found: {endpoint}") from e
            raise TEMdbClientError(f"HTTP {e.response.status_code}: {e.response.text}") from e
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

    async def __aenter__(self) -> "AsyncTEMdbClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()


class SyncTEMdbClient:
    def __init__(
        self,
        base_url: str,
        api_version: str = "v2",
        api_key: str | None = None,
        timeout: float = 30.0,
        debug: bool = False,
    ):
        self._async_client = AsyncTEMdbClient(base_url, api_version, api_key, timeout, debug)
        self.logger = logging.getLogger("temdb_client.sync")
        level = logging.DEBUG if debug else logging.INFO
        self.logger.setLevel(level)
        self.logger.info(f"Sync TEMdb client initialized (wrapping async): {base_url} (API v{api_version})")

        self._acquisition = SyncAcquisitionResourceWrapper(self._async_client.acquisition)
        self._specimen = SyncSpecimenResourceWrapper(self._async_client.specimen)
        self._block = SyncBlockResourceWrapper(self._async_client.block)
        self._cutting_session = SyncCuttingSessionResourceWrapper(self._async_client.cutting_session)
        self._substrate = SyncSubstrateResourceWrapper(self._async_client.substrate)
        self._acquisition_task = SyncAcquisitionTaskResourceWrapper(self._async_client.acquisition_task)
        self._roi = SyncROIResourceWrapper(self._async_client.roi)
        self._section = SyncSectionResourceWrapper(self._async_client.section)

    @property
    def acquisition(self) -> SyncAcquisitionResourceWrapper:
        return self._acquisition

    @property
    def specimen(self) -> SyncSpecimenResourceWrapper:
        return self._specimen

    @property
    def block(self) -> SyncBlockResourceWrapper:
        return self._block

    @property
    def cutting_session(self) -> SyncCuttingSessionResourceWrapper:
        return self._cutting_session

    @property
    def substrate(self) -> SyncSubstrateResourceWrapper:
        return self._substrate

    @property
    def acquisition_task(self) -> SyncAcquisitionTaskResourceWrapper:
        return self._acquisition_task

    @property
    def roi(self) -> SyncROIResourceWrapper:
        return self._roi

    @property
    def section(self) -> SyncSectionResourceWrapper:
        return self._section

    def health_check(self) -> dict[str, Any]:
        """Check if the API is available."""
        self.logger.info("Running sync health check...")
        try:
            return asyncio.run(self._async_client.health_check())
        except Exception as e:
            self.logger.error(f"Sync Health check failed: {str(e)}")
            raise

    def get_api_info(self) -> dict[str, Any]:
        """Get API information."""
        self.logger.info("Getting sync API info...")
        return asyncio.run(self._async_client.get_api_info())

    def close(self) -> None:
        self.logger.info("Closing sync TEMdb client (and underlying async client)")
        asyncio.run(self._async_client.close())

    def __enter__(self) -> "SyncTEMdbClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def create_client(
    base_url: str,
    api_version: str = "v2",
    api_key: str | None = None,
    timeout: float = 30.0,
    debug: bool = False,
    async_mode: bool = True,
) -> AsyncTEMdbClient | SyncTEMdbClient:
    """
    Factory function to create either an async or sync TEMdb client.

    Args:
        base_url: Base URL of the TEMdb API (e.g., "http://localhost:8000").
        api_version: API version string (default: "v2").
        api_key: Optional API key for authentication.
        timeout: Request timeout in seconds.
        debug: Enable debug logging for the client.
        async_mode: If True (default), returns AsyncTEMdbClient. If False, returns SyncTEMdbClient.

    Returns:
        An instance of AsyncTEMdbClient or SyncTEMdbClient.
    """
    if async_mode:
        return AsyncTEMdbClient(base_url, api_version, api_key, timeout, debug)
    else:
        return SyncTEMdbClient(base_url, api_version, api_key, timeout, debug)
