# app/database/dependencies.py
from fastapi import Depends
from typing import Callable
from temdb.database import DatabaseManager
from starlette.requests import Request

def get_db_manager(request: Request):
    return request.app.state.db_manager

async def get_dynamic_model_dependency(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> Callable:
    return db_manager.get_dynamic_model