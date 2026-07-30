import logging

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from temdb.server.sqlmodels import (
    AcquisitionSQLModel,
    AcquisitionTaskSQLModel,
    Base,
    BlockSQLModel,
    CuttingSessionSQLModel,
    DatasetSQLModel,
    LensCorrectionSQLModel,
    MicroscopeSQLModel,
    ROISQLModel,
    SectionSQLModel,
    SpecimenSQLModel,
    SubstrateSQLModel,
    TileSQLModel,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLAlchemy database connections and schema initialization."""

    def __init__(
        self,
        database_url: str | None = None,
    ):
        self.database_url = database_url
        self.sql_engine: AsyncEngine | None = (
            create_async_engine(
                database_url,
                echo=False,
                pool_pre_ping=True,
                pool_recycle=1800,
                connect_args={
                    "server_settings": {"application_name": "temdb"},  # attributable pg_stat_activity / slow-query logs
                    "command_timeout": 30,  # backstop against a hung query pinning a pool slot
                },
            )
            if database_url
            else None
        )
        self.async_session_factory: async_sessionmaker[AsyncSession] | None = (
            async_sessionmaker(bind=self.sql_engine, expire_on_commit=False) if self.sql_engine else None
        )
        # Ensure metadata for ORM entities is registered.
        self._sql_models = (
            SpecimenSQLModel,
            DatasetSQLModel,
            BlockSQLModel,
            CuttingSessionSQLModel,
            SubstrateSQLModel,
            SectionSQLModel,
            ROISQLModel,
            AcquisitionTaskSQLModel,
            AcquisitionSQLModel,
            TileSQLModel,
            MicroscopeSQLModel,
            LensCorrectionSQLModel,
        )

    async def initialize(self, create_schema: bool = True):
        if not create_schema:
            return
        async with self.sql_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def dispose(self):
        """Dispose the engine and its connection pool (call on app shutdown)."""
        if self.sql_engine is not None:
            await self.sql_engine.dispose()
