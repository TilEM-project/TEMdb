import logging
from typing import Type, TypeVar, List, Dict

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document

from copy import deepcopy
from temdb.models.v1.grids import Grid

from temdb.models.v2.specimen import Specimen
from temdb.models.v2.block import Block
from temdb.models.v2.cutting_session import CuttingSession
from temdb.models.v2.section import Section
from temdb.models.v2.roi import ROI
from temdb.models.v2.imaging_session import ImagingSession
from temdb.models.v2.acquisition import Acquisition

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TDocument = TypeVar("TDocument", bound=Document)


class DatabaseManager:

    def __init__(self, mongo_url: str, db_name: str):
        self.mongo_url = mongo_url
        self.db_name = db_name
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        self._static_models: List[Type[Document]] = [
            Grid,
            Specimen,
            Block,
            CuttingSession,
            Section,
            ROI,
            ImagingSession,
            Acquisition,
        ]

        self._dynamic_models: Dict[str, Type[Document]] = {}

    async def initialize(self):

        await init_beanie(database=self.db, document_models=self._static_models)

    async def get_dynamic_model(
        self, document_class: Type[TDocument], collection_name: str
    ) -> Type[TDocument]:

        # check if model is already initialized in dict
        if self._dynamic_models.get(collection_name):
            return self._dynamic_models[collection_name]
        DynamicDocument = deepcopy(document_class)
        
        # Modify the Settings inner class
        if hasattr(DynamicDocument, "Settings"):
            DynamicDocument.Settings.name = collection_name
        else:

            class Settings:
                name = collection_name

            setattr(DynamicDocument, "Settings", Settings)

        DynamicDocument.__name__ = f"{document_class.__name__}_{collection_name}"

        await init_beanie(database=self.db, document_models=[DynamicDocument])

        # add model to dict of initialized models
        self._dynamic_models[collection_name] = DynamicDocument

        return DynamicDocument

    async def set_database(self, db_name: str):
        self.db = self.client[db_name]
        await self.initialize()
        return self.db
