from temdb.models import LensCorrectionCreate, LensCorrectionResponse, LensCorrectionUpdate

from .base import BaseResource, kwargs2model


class LensCorrectionResource(BaseResource):
    """Resource class for interacting with Lens Correction endpoints."""

    @kwargs2model(LensCorrectionCreate)
    async def create(self, data: LensCorrectionCreate) -> LensCorrectionResponse:
        """Record a completed lens-correction solve."""
        payload = await self._post("lens-corrections", data=data.model_dump(exclude_unset=True, mode="json"))
        return LensCorrectionResponse.model_validate(payload)

    async def get(self, lc_id: str) -> LensCorrectionResponse:
        """Get a lens correction by its UUID lc_id."""
        return LensCorrectionResponse.model_validate(await self._get(f"lens-corrections/{lc_id}"))

    async def get_current(self, microscope_id: str, magnification: int) -> LensCorrectionResponse:
        """Get the most recent lens correction for a (microscope, magnification) pair."""
        return LensCorrectionResponse.model_validate(
            await self._get(
                "lens-corrections/current",
                params={"microscope_id": microscope_id, "magnification": magnification},
            )
        )

    async def list(
        self,
        microscope_id: str | None = None,
        magnification: int | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[LensCorrectionResponse]:
        """List lens corrections, newest-first, optionally filtered."""
        params = {"microscope_id": microscope_id, "magnification": magnification, "skip": skip, "limit": limit}
        params = {k: v for k, v in params.items() if v is not None}
        data = await self._get("lens-corrections", params=params)
        return [LensCorrectionResponse.model_validate(i) for i in data] if isinstance(data, list) else []

    @kwargs2model(LensCorrectionUpdate)
    async def update(self, lc_id: str, data: LensCorrectionUpdate) -> LensCorrectionResponse:
        """Backfill artifacts on a lens correction."""
        payload = await self._patch(f"lens-corrections/{lc_id}", data=data.model_dump(exclude_unset=True, mode="json"))
        return LensCorrectionResponse.model_validate(payload)
