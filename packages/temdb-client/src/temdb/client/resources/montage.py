from collections.abc import AsyncIterator
from typing import Any

from temdb.models import AsyncTileSpecData, PaginatedTileResponse, TileResponse, TileSpecMetadata

from .base import BaseResource


class MontageResource(BaseResource):
    """Resource for montage tilespec export operations."""

    async def get_tilespec_metadata(self, montage_id: str) -> TileSpecMetadata:
        """Fetch acquisition/hierarchy metadata for TileSpec generation."""
        response_data = await self._get(f"montages/{montage_id}/tilespec-metadata")
        return TileSpecMetadata.model_validate(response_data)

    async def get_tiles_page(
        self,
        montage_id: str,
        cursor: int | None = None,
        limit: int = 1000,
    ) -> PaginatedTileResponse:
        """Fetch a page of tiles for a montage."""
        params: dict[str, Any] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor

        response_data = await self._get(f"montages/{montage_id}/tiles", params=params)
        return PaginatedTileResponse.model_validate(response_data)

    async def iter_tiles(
        self,
        montage_id: str,
        batch_size: int = 1000,
    ) -> AsyncIterator[TileResponse]:
        """
        Async generator that yields tiles for a montage.

        Handles pagination internally, enabling memory-efficient processing
        of large montages (100-200k tiles).

        Args:
            montage_id: The montage identifier
            batch_size: Number of tiles to fetch per request (default 1000)

        Yields:
            TileResponse objects
        """
        cursor = None
        while True:
            page = await self.get_tiles_page(montage_id, cursor=cursor, limit=batch_size)
            for tile in page.tiles:
                yield tile

            if not page.metadata.get("has_more", False):
                break

            cursor = page.metadata.get("next_cursor")

    async def get_tilespec_data(
        self,
        montage_id: str,
        batch_size: int = 1000,
    ) -> AsyncTileSpecData:
        """
        Get combined metadata and tile iterator for TileSpec generation.

        Fetches metadata once upfront, then provides a lazy tile iterator.
        This is the recommended way to build TileSpec objects for a montage.

        Args:
            montage_id: The montage identifier
            batch_size: Number of tiles to fetch per request (default 1000)

        Returns:
            AsyncTileSpecData with metadata and async tile iterator

        Example:
            result = await client.montage.get_tilespec_data("MONTAGE_001")
            async for tile in result.tiles:
                tilespec = TileSpec(
                    tileId=tile.tile_id,
                    width=result.metadata.width,
                    ...
                )
        """
        metadata = await self.get_tilespec_metadata(montage_id)
        return AsyncTileSpecData(
            metadata=metadata,
            tiles=self.iter_tiles(montage_id, batch_size=batch_size),
        )
