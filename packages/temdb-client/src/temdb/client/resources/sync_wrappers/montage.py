import asyncio
from collections.abc import Iterator

from temdb.models import PaginatedTileResponse, TileResponse, TileSpecData, TileSpecMetadata

from ..montage import MontageResource


class SyncMontageResourceWrapper:
    """Synchronous wrapper for the MontageResource."""

    def __init__(self, async_resource: MontageResource):
        self._async_resource = async_resource

    def get_tilespec_metadata(self, montage_id: str) -> TileSpecMetadata:
        """Get tilespec metadata synchronously."""
        return asyncio.run(self._async_resource.get_tilespec_metadata(montage_id))

    def get_tiles_page(
        self,
        montage_id: str,
        cursor: int | None = None,
        limit: int = 1000,
    ) -> PaginatedTileResponse:
        """Get a page of tiles synchronously."""
        return asyncio.run(self._async_resource.get_tiles_page(montage_id, cursor=cursor, limit=limit))

    def iter_tiles(
        self,
        montage_id: str,
        batch_size: int = 1000,
    ) -> Iterator[TileResponse]:
        """
        Synchronous generator that yields tiles for a montage.

        Args:
            montage_id: The montage identifier
            batch_size: Number of tiles to fetch per request

        Yields:
            TileResponse objects
        """
        cursor = None
        while True:
            page = self.get_tiles_page(montage_id, cursor=cursor, limit=batch_size)
            yield from page.tiles

            if not page.metadata.get("has_more", False):
                break

            cursor = page.metadata.get("next_cursor")

    def get_tilespec_data(
        self,
        montage_id: str,
        batch_size: int = 1000,
    ) -> TileSpecData:
        """
        Get combined metadata and tile iterator for TileSpec generation.

        Fetches metadata once upfront, then provides a lazy tile iterator.
        This is the recommended way to build TileSpec objects for a montage.

        Args:
            montage_id: The montage identifier
            batch_size: Number of tiles to fetch per request (default 1000)

        Returns:
            TileSpecData with metadata and tile iterator

        Example:
            result = client.montage.get_tilespec_data("MONTAGE_001")
            for tile in result.tiles:
                tilespec = TileSpec(
                    tileId=tile.tile_id,
                    width=result.metadata.width,
                    ...
                )
        """
        metadata = self.get_tilespec_metadata(montage_id)
        return TileSpecData(
            metadata=metadata,
            tiles=self.iter_tiles(montage_id, batch_size=batch_size),
        )
