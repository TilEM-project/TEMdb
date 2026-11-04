from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class DatabaseManager:
    """Manages the SQLAlchemy engine and session factory."""

    def __init__(self, database_url: str):
        self.sql_engine: AsyncEngine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=1800,
            connect_args={
                "server_settings": {"application_name": "temdb"},  # attributable pg_stat_activity / slow-query logs
                "command_timeout": 30,  # backstop against a hung query pinning a pool slot
            },
        )
        self.async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self.sql_engine, expire_on_commit=False
        )

    async def dispose(self):
        """Dispose the engine and its connection pool (call on app shutdown)."""
        await self.sql_engine.dispose()
