from typing import Dict, Optional
from pydantic import BaseModel
from beanie import Document, Link

from pymongo import IndexModel, ASCENDING

from temdb.models.v2.specimen import Specimen


class BlockCreate(BaseModel):
    block_id: str
    microCT_info: Dict
    specimen_id: str


class BlockUpdate(BaseModel):
    block_id: Optional[str] = None
    microCT_info: Optional[Dict] = None


class Block(Document):
    block_id: str
    microCT_info:Optional[Dict]
    specimen_id: Link[Specimen]

    class Settings:
        name = "blocks"
        indexes = [
            IndexModel([("block_id", ASCENDING)], unique=True, name="block_id_index"),
            IndexModel(
                [("specimen_id.id", ASCENDING), ("name", ASCENDING)],
                name="specimen_name_index",
            ),
            IndexModel(
                [("specimen_id.id", ASCENDING), ("block_id", ASCENDING)],
                name="specimen_block_index",
            ),
        ]
