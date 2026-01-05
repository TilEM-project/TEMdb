from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BlockBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    microCT_info: dict[str, Any] | None = Field(None, description="MicroCT information of block")


class BlockCreate(BlockBase):
    block_id: str = Field(..., description="Unique block identifier")
    specimen_id: str = Field(..., description="Parent specimen ID")


class BlockUpdate(BlockBase):
    pass


class BlockResponse(BlockBase):
    block_id: str = Field(..., description="Unique block identifier")
    specimen_id: str = Field(..., description="Parent specimen ID")

    created_at: datetime | None = None
    updated_at: datetime | None = None
