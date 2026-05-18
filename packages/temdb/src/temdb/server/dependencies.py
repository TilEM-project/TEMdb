from collections.abc import AsyncIterator

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from temdb.server.database import DatabaseManager


def get_db_manager(request: Request):
    return request.app.state.db_manager


async def get_async_session(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> AsyncIterator[AsyncSession]:
    if db_manager.async_session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SQL database is not configured. Set DATABASE_URL to enable SQLAlchemy-backed endpoints.",
        )

    async with db_manager.async_session_factory() as session:
        yield session
