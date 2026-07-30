from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from .base import TEMDBModel


class BlockBase(TEMDBModel):
    microCT_info: dict[str, Any] | None = Field(None, description="MicroCT information of block")
    description: str | None = Field(None, description="Description of block")


class BlockCreate(BlockBase):
    block_id: str = Field(..., description="Unique block identifier")
    specimen_id: str = Field(..., description="Parent specimen ID")
    created_at: datetime | None = Field(None, description="Creation timestamp; server-generated if omitted")


class BlockUpdate(BlockBase):
    pass


class BlockResponse(BlockBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    block_id: str = Field(..., description="Unique block identifier")
    specimen_id: str = Field(..., description="Parent specimen ID")

    created_at: datetime | None = None
    updated_at: datetime | None = None
