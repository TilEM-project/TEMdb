import logging

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie


from temdb.models.v1.grids import Grid

from temdb.models.v2.specimen import Specimen
from temdb.models.v2.block import Block
from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.section import Section
from temdb.models.v2.roi import ROI
from temdb.models.v2.imaging_session import ImagingSession
from temdb.models.v2.acquisition import Acquisition
from temdb.models.v2.tile import Tile


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db(mongo_url: str, db_name: str):

    document_models = [
        Grid, # original metadata schema
        Specimen,
        Block,
        CuttingSession,
        Section,
        ROI,
        ImagingSession,
        Acquisition,
        Tile,
    ]

    try:
        client = AsyncIOMotorClient(mongo_url)
        db = client[db_name]
        await init_beanie(db, document_models=document_models)

        collections = await db.list_collection_names()
        logger.debug(f"Collections in database: {collections}")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise
