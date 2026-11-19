from typing import Generic, TypeVar

from pydantic import Field

from temdb.models.base import TEMDBModel

T = TypeVar("T")


class Page(TEMDBModel, Generic[T]):
    items: list[T] = Field(..., description="The rows of this page")
    next_cursor: str | None = Field(None, description="Pass as cursor to get the next page; null on the last page")
    total: int | None = Field(
        None, description="Rows matching the filters, over all pages; null on pages fetched by cursor"
    )
