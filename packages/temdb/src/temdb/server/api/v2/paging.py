import base64
import json
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Query, status
from sqlalchemy import ColumnElement, Select, and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import operators


@dataclass
class Position:
    """Where a page starts: after a cursor, or at an offset."""

    cursor: str | None = Query(None, description="next_cursor of the previous page")
    offset: int | None = Query(
        None,
        ge=0,
        description=(
            "Rows to skip, for jumping to a page; pages can shift by a row if rows are added or deleted "
            "between requests. Continue with next_cursor to avoid that."
        ),
    )

    def __post_init__(self):
        if self.cursor is not None and self.offset is not None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "send cursor or offset, not both")


async def page(
    session: AsyncSession,
    statement: Select,
    *,
    key: Sequence[Any],
    at: Position,
    limit: int,
    scalars: bool = True,
    count: bool = True,
) -> dict[str, Any]:
    """One page of the statement in key order as items, the cursor for the next page and the rows matching."""
    cursor, offset = at.cursor, at.offset
    columns = [_column(item) for item in key]
    names = [f"{column.table.name}.{column.key}{' desc' if descending else ''}" for column, descending in columns]
    total = None
    if count and cursor is None:
        total = await session.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    statement = statement.order_by(*key)
    if cursor is not None:
        statement = statement.where(_after(columns, _decode(cursor, names, columns)))
    if offset:
        statement = statement.offset(offset)
    paged = statement.limit(limit + 1)
    rows = (await session.scalars(paged)).all() if scalars else (await session.execute(paged)).all()
    next_cursor = None
    if len(rows) > limit:
        last = rows[limit - 1] if scalars else rows[limit - 1][0]
        next_cursor = _encode(names, [getattr(last, column.key) for column, _ in columns])
    return {"items": list(rows[:limit]), "next_cursor": next_cursor, "total": total}


def _column(item: Any) -> tuple[ColumnElement, bool]:
    descending = getattr(item, "modifier", None) is operators.desc_op
    return (item.element if descending else item).expression, descending


def _after(columns: list[tuple[ColumnElement, bool]], values: list[Any]) -> ColumnElement:
    # Postgres sorts NULLS LAST ascending and NULLS FIRST descending
    steps = []
    for index, ((column, descending), value) in enumerate(zip(columns, values)):
        ties = [
            earlier.is_(None) if tied is None else earlier == tied
            for (earlier, _), tied in zip(columns[:index], values[:index])
        ]
        if descending:
            step = column.is_not(None) if value is None else column < value
        else:
            step = false() if value is None else or_(column > value, column.is_(None))
        steps.append(and_(*ties, step))
    return or_(*steps)


def _encode(names: list[str], values: list[Any]) -> str:
    text = json.dumps({"key": names, "values": values}, default=str)
    return base64.urlsafe_b64encode(text.encode()).decode()


def _decode(cursor: str, names: list[str], columns: list[tuple[ColumnElement, bool]]) -> list[Any]:
    try:
        token = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        if token["key"] != names or len(token["values"]) != len(names):
            raise ValueError
        return [_typed(value, column) for value, (column, _) in zip(token["values"], columns)]
    except (ValueError, TypeError, KeyError, AttributeError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "cursor is not from this listing")


def _typed(value: Any, column: ColumnElement) -> Any:
    """The cursor value as the column's Python type; ValueError when it has another type."""
    try:
        python_type = column.type.python_type
    except NotImplementedError:
        return value
    if value is None or python_type is object:
        return value
    if python_type is datetime:
        return datetime.fromisoformat(value)
    if python_type is uuid.UUID:
        return uuid.UUID(value)
    if python_type is float and type(value) is int:
        return float(value)
    if type(value) is not python_type:
        raise ValueError
    return value
