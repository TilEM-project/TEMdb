import logging

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie


from temdb.models.specimen import Specimen
from temdb.models.block import Block
from temdb.models.cutting_session import CuttingSession
from temdb.models.section import Section
from temdb.models.roi import ROI
from temdb.models.imaging_session import ImagingSession
from temdb.models.acquisition import Acquisition
from temdb.models.tile import Tile


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db(mongo_url: str, db_name: str):

    document_models = [
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
