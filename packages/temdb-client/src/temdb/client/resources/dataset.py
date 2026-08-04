from typing import Any

from temdb.models import DatasetCreate, DatasetResponse, DatasetUpdate

from .base import BaseResource, kwargs2model


class DatasetResource(BaseResource):
    """Resource class for interacting with Dataset endpoints."""

    @kwargs2model(DatasetCreate)
    async def create(self, dataset_data: DatasetCreate) -> DatasetResponse:
        """Create a new dataset."""
        response_data = await self._post("datasets", data=dataset_data.model_dump(exclude_unset=True))
        return DatasetResponse.model_validate(response_data)

    async def get(self, dataset_id: str) -> DatasetResponse:
        """Get a dataset by its UUID dataset_id."""
        response_data = await self._get(f"datasets/{dataset_id}")
        return DatasetResponse.model_validate(response_data)

    async def get_by_name(self, name: str) -> DatasetResponse:
        """Get a dataset by its unique human-readable name."""
        response_data = await self._get(f"datasets/by-name/{name}")
        return DatasetResponse.model_validate(response_data)

    async def list(
        self,
        specimen_id: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
        **kwargs: Any,
    ) -> list[DatasetResponse]:
        """List datasets, optionally filtered by specimen_id and/or status."""
        params = {"specimen_id": specimen_id, "status": status, "skip": skip, "limit": limit}
        params = {k: v for k, v in params.items() if v is not None}
        params.update(kwargs)
        response_data = await self._get("datasets", params=params)
        return (
            [DatasetResponse.model_validate(item) for item in response_data] if isinstance(response_data, list) else []
        )

    @kwargs2model(DatasetUpdate)
    async def update(self, dataset_id: str, dataset_data: DatasetUpdate) -> DatasetResponse:
        """Update a dataset (e.g. status, description)."""
        response_data = await self._patch(f"datasets/{dataset_id}", data=dataset_data.model_dump(exclude_unset=True))
        return DatasetResponse.model_validate(response_data)

    async def create_with_estimate(
        self,
        name: str,
        *,
        estimated_tile_count: int | None = None,
        estimated_roi_count: int | None = None,
        tiles_per_roi: int | None = None,
        **fields: Any,
    ) -> DatasetResponse:
        """Create a dataset from an estimated tile count; the server resolves size_class.

        Provide either ``estimated_tile_count`` directly, or both
        ``estimated_roi_count`` and ``tiles_per_roi`` (their product is used).
        """
        if estimated_tile_count is not None:
            total = estimated_tile_count
        elif estimated_roi_count is not None and tiles_per_roi is not None:
            total = estimated_roi_count * tiles_per_roi
        else:
            raise ValueError("Provide estimated_tile_count, or both estimated_roi_count and tiles_per_roi")
        return await self.create(DatasetCreate(name=name, estimated_tile_count=total, **fields))
