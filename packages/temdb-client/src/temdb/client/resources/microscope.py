from temdb.models import MicroscopeCreate, MicroscopeResponse, MicroscopeUpdate

from .base import BaseResource


class MicroscopeResource(BaseResource):
    """Resource class for interacting with Microscope endpoints."""

    async def create(self, data: MicroscopeCreate) -> MicroscopeResponse:
        """Register a new microscope."""
        payload = await self._post("microscopes", data=data.model_dump(exclude_unset=True, mode="json"))
        return MicroscopeResponse.model_validate(payload)

    async def get(self, id_or_label: str) -> MicroscopeResponse:
        """Get a microscope by UUID microscope_id or unique label."""
        return MicroscopeResponse.model_validate(await self._get(f"microscopes/{id_or_label}"))

    async def list(self, skip: int = 0, limit: int = 50) -> list[MicroscopeResponse]:
        """List microscopes."""
        data = await self._get("microscopes", params={"skip": skip, "limit": limit})
        return [MicroscopeResponse.model_validate(i) for i in data] if isinstance(data, list) else []

    async def update(self, microscope_id: str, data: MicroscopeUpdate) -> MicroscopeResponse:
        """Update microscope metadata."""
        payload = await self._patch(f"microscopes/{microscope_id}", data=data.model_dump(exclude_unset=True, mode="json"))
        return MicroscopeResponse.model_validate(payload)
