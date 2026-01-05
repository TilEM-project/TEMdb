import logging
from copy import deepcopy
from typing import TypeVar

from beanie import Document, init_beanie
from pymongo import AsyncMongoClient
from temdb.server.documents import (
    AcquisitionDocument,
    AcquisitionTaskDocument,
    BlockDocument,
    CuttingSessionDocument,
    GridDocument,
    ROIDocument,
    SectionDocument,
    SpecimenDocument,
    SubstrateDocument,
    TileDocument,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TDocument = TypeVar("TDocument", bound=Document)


class DatabaseManager:
    """Manages database connections and Beanie document initialization."""

    def __init__(self, mongodb_uri: str, mongodb_name: str):
        self.mongo_url = mongodb_uri
        self.db_name = mongodb_name
        self.client = AsyncMongoClient(mongodb_uri)
        self.db = self.client[mongodb_name]
        self._static_models: list[type[Document]] = [
            SpecimenDocument,
            BlockDocument,
            CuttingSessionDocument,
            SubstrateDocument,
            SectionDocument,
            ROIDocument,
            AcquisitionTaskDocument,
            AcquisitionDocument,
            TileDocument,
            GridDocument,
        ]

        self._dynamic_models: dict[str, type[Document]] = {}

    async def initialize(self):
        await init_beanie(database=self.db, document_models=self._static_models)

    async def get_dynamic_model(self, document_class: type[TDocument], collection_name: str) -> type[TDocument]:
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
