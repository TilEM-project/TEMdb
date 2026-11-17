import asyncio
import gzip
import importlib.metadata
import json
import logging
from typing import Any, cast

import httpx
from pydantic_core import to_jsonable_python

from .exceptions import TEMdbClientError, TEMdbContractError, TEMdbNotFoundError, TEMdbServerError
from .resources.acquisition import AcquisitionResource
from .resources.block import BlockResource
from .resources.cutting_session import CuttingSessionResource
from .resources.dataset import DatasetResource
from .resources.layout import SubstrateLayoutResource
from .resources.lens_correction import LensCorrectionResource
from .resources.microscope import MicroscopeResource
from .resources.roi import ROIResource
from .resources.section import SectionResource
from .resources.specimen import SpecimenResource
from .resources.substrate import SubstrateResource
from .resources.task import AcquisitionTaskResource


class TEMdbClient:
    specimen: SpecimenResource
    block: BlockResource
    cutting_session: CuttingSessionResource
    substrate: SubstrateResource
    acquisition_task: AcquisitionTaskResource
    roi: ROIResource
    acquisition: AcquisitionResource
    dataset: DatasetResource
    section: SectionResource
    microscope: MicroscopeResource
    lens_correction: LensCorrectionResource
    substrate_layout: SubstrateLayoutResource

    def __init__(
        self,
        base_url: str,
        api_version: str = "v2",
        api_key: str | None = None,
        timeout: float = 30.0,
        debug: bool = False,
        transport: httpx.AsyncBaseTransport | None = None,
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
            transport=transport,
        )
        self._file_client = httpx.AsyncClient(timeout=timeout)

        self.logger.info(f"Async TEMdb client initialized: {base_url} (API v{api_version})")
        self.contract: dict[str, Any] | None = None
        self._contract_lock = asyncio.Lock()

        self.specimen = SpecimenResource(self._api_request, self.api_url)
        self.block = BlockResource(self._api_request, self.api_url)
        self.cutting_session = CuttingSessionResource(self._api_request, self.api_url)
        self.substrate = SubstrateResource(self._api_request, self.api_url)
        self.acquisition_task = AcquisitionTaskResource(self._api_request, self.api_url)
        self.roi = ROIResource(self._api_request, self.api_url)
        self.acquisition = AcquisitionResource(self._api_request, self.api_url, file_client=self._file_client)
        self.dataset = DatasetResource(self._api_request, self.api_url)
        self.section = SectionResource(self._api_request, self.api_url, file_client=self._file_client)
        self.microscope = MicroscopeResource(self._api_request, self.api_url)
        self.lens_correction = LensCorrectionResource(self._api_request, self.api_url)
        self.substrate_layout = SubstrateLayoutResource(self._api_request, self.api_url)

    async def _async_request(
        self, method: str, endpoint: str, *, with_headers: bool = False, **kwargs
    ) -> dict[str, Any] | list[Any] | tuple[dict[str, Any] | list[Any], httpx.Headers]:
        """Send a request and return its JSON body, or (body, response headers) with with_headers=True."""
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
            data = {} if response.status_code == 204 else response.json()
            return (data, response.headers) if with_headers else data
        except httpx.HTTPStatusError as e:
            level = logging.WARNING if e.response.status_code < 500 else logging.ERROR
            self.logger.log(level, f"HTTP error: {e.response.status_code} - {e.response.text}")
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
            result = await self._async_request("GET", f"{self.raw_base_url}/health")
            self.logger.info(f"Async Health check: {result.get('status', 'unknown')}")
            return cast(dict[str, Any], result)
        except Exception as e:
            self.logger.error(f"Async Health check failed: {str(e)}")
            raise

    async def get_api_info(self) -> dict[str, Any]:
        """Get API information."""
        result = await self._async_request("GET", f"{self.raw_base_url}/")
        return cast(dict[str, Any], result)

    async def close(self) -> None:
        self.logger.info("Closing async TEMdb client")
        try:
            await self._http_client.aclose()
        finally:
            await self._file_client.aclose()

    async def check_contract(self) -> dict[str, Any]:
        """Check server contract compatibility with this client's model version."""
        try:
            contract = await self._async_request("GET", "contract")
        except TEMdbNotFoundError as error:
            raise TEMdbContractError(
                f"{self.raw_base_url} has no /contract route; it is older than TEMdb 4.0 and this client needs 4.x"
            ) from error
        if not isinstance(contract, dict) or not isinstance(contract.get("models_version"), str):
            raise TEMdbContractError(f"{self.raw_base_url} answered /contract without a models_version: {contract!r}")
        ours = importlib.metadata.version("temdb-models")
        theirs = contract["models_version"]
        if ours.split(".")[0] != theirs.split(".")[0]:
            raise TEMdbContractError(
                f"{self.raw_base_url} serves models {theirs}; this client was built against models {ours}"
            )
        self.contract = contract
        return contract

    async def _api_request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any] | list[Any]:
        if self.contract is None:
            async with self._contract_lock:
                if self.contract is None:
                    await self.check_contract()
        return await self._async_request(method, endpoint, **kwargs)

    async def __aenter__(self) -> "TEMdbClient":
        try:
            await self.check_contract()
        except BaseException:
            await self.close()
            raise
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()
