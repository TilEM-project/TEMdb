from typing import Any

from fastapi import Response
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

from temdb.models import HAS_MORE_HEADER


async def page(
    session: AsyncSession, statement: Select, *, skip: int, limit: int, response: Response, scalars: bool = True
) -> list[Any]:
    """Run one page of an ordered statement and set X-Has-More to whether rows follow it."""
    paged = statement.offset(skip).limit(limit + 1)
    rows = (await session.scalars(paged)).all() if scalars else (await session.execute(paged)).all()
    response.headers[HAS_MORE_HEADER] = "true" if len(rows) > limit else "false"
    return list(rows[:limit])
