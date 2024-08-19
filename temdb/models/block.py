from typing import Dict, Optional
from pydantic import BaseModel
from beanie import Document, Link, PydanticObjectId

from pymongo import IndexModel, ASCENDING

from temdb.models.specimen import Specimen


class BlockCreate(BaseModel):
    block_id: str
    name: str
    microCT_Info: Dict
    specimen_id: PydanticObjectId


class BlockUpdate(BaseModel):
    name: Optional[str] = None
    microCT_Info: Optional[Dict] = None


class Block(Document):
    block_id: str
    name: str
    microCT_Info: Dict
    specimen: Link[Specimen]

    class Settings:
        name = "blocks"
        indexes = [
            IndexModel([("block_id", ASCENDING)], unique=True, name="block_id_index"),
            IndexModel(
                [("specimen.id", ASCENDING), ("name", ASCENDING)],
                name="specimen_name_index",
            ),
            IndexModel(
                [("specimen.id", ASCENDING), ("block_id", ASCENDING)],
                name="specimen_block_index",
            ),
        ]
