from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from temdb.server.database import DatabaseManager


def get_db_manager(request: Request):
    return request.app.state.db_manager


async def get_async_session(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> AsyncIterator[AsyncSession]:
    async with db_manager.async_session_factory() as session:
        yield session


def get_storage_client_manager(request: Request):
    return request.app.state.storage_client_manager
