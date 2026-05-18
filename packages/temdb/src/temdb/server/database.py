import logging

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import Select

from temdb.server.sqlmodels import (
    AcquisitionSQLModel,
    AcquisitionTaskSQLModel,
    Base,
    BlockSQLModel,
    CuttingSessionSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SpecimenSQLModel,
    SubstrateSQLModel,
    TileSQLModel,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TEMDBAsyncSession(AsyncSession):
    async def exec(self, statement: Select, *args, **kwargs):
        result = await self.execute(statement, *args, **kwargs)
        return result.scalars()


class DatabaseManager:
    """Manages SQLAlchemy database connections and schema initialization."""

    def __init__(
        self,
        database_url: str | None = None,
    ):
        self.database_url = database_url
        self.sql_engine: AsyncEngine | None = (
            create_async_engine(database_url, echo=False, pool_pre_ping=True) if database_url else None
        )
        self.async_session_factory: async_sessionmaker[TEMDBAsyncSession] | None = (
            async_sessionmaker(bind=self.sql_engine, class_=TEMDBAsyncSession, expire_on_commit=False)
            if self.sql_engine
            else None
        )
        # Ensure metadata for ORM entities is registered.
        self._sql_models = (
            SpecimenSQLModel,
            BlockSQLModel,
            CuttingSessionSQLModel,
            SubstrateSQLModel,
            SectionSQLModel,
            ROISQLModel,
            AcquisitionTaskSQLModel,
            AcquisitionSQLModel,
            TileSQLModel,
        )

    async def initialize(self):
        if self.sql_engine is not None:
            async with self.sql_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
