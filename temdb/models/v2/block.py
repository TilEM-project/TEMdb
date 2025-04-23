from typing import Dict, Optional
from pydantic import BaseModel, Field
from beanie import Document, Link

from pymongo import IndexModel, ASCENDING

from temdb.models.v2.specimen import Specimen


class BlockCreate(BaseModel):
    block_id: str = Field(..., description="Block ID of specimen")
    microCT_info: Optional[Dict] = Field(
        ..., description="MicroCT information of block"
    )
    specimen_id: str = Field(..., description="ID of specimen")


class BlockUpdate(BaseModel):
    microCT_info: Optional[Dict] = Field(
        None, description="MicroCT information of block"
    )


class Block(Document):
    block_id: str = Field(..., description="Block ID of specimen")
    microCT_info: Optional[Dict] = Field(
        None, description="MicroCT information of block"
    )
    specimen_ref: Link[Specimen] = Field(..., description="ID of specimen")
    specimen_id: str = Field(
        ..., description="Human-readable ID of the parent Specimen"
    )

    class Settings:
        name = "blocks"
        indexes = [
            IndexModel([("block_id", ASCENDING)], unique=True, name="block_id_index"),
            IndexModel([("specimen_id", ASCENDING)], name="specimen_id_index"),
            IndexModel(
                [("specimen_ref.id", ASCENDING), ("block_id", ASCENDING)],
                name="specimen_ref_block_id_index",
                unique=True,
            ),
        ]
