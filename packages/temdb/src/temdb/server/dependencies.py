from collections.abc import Callable

from fastapi import Depends
from starlette.requests import Request
from temdb.server.database import DatabaseManager


def get_db_manager(request: Request):
    return request.app.state.db_manager


async def get_dynamic_model_dependency(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> Callable:
    return db_manager.get_dynamic_model
