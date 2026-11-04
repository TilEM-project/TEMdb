from typing import Any

from fastapi import HTTPException
from sqlalchemy import Text, literal
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from temdb.models import APIErrorResponse

error_responses = {400: {"model": APIErrorResponse}, 404: {"model": APIErrorResponse}, 409: {"model": APIErrorResponse}}


def check_image_update(stored: dict[str, Any] | None, sent: dict[str, Any] | None, owner: str) -> None:
    """Refuse an image update that would clear or replace the stored image of owner."""
    if sent is None:
        raise HTTPException(400, f"Delete the image of {owner} through its image route")
    if stored is not None and stored != sent:
        raise HTTPException(409, f"Delete the existing image of {owner} before setting a new one")


def drop_null_keys(extra: dict[str, Any] | None) -> dict[str, Any]:
    """Return a copy without the keys set to None: {"a": 1, "b": None} becomes {"a": 1}, and None becomes {}."""
    return {key: value for key, value in (extra or {}).items() if value is not None}


def merge_extra(column, changes: dict[str, Any]):
    """Return a SQL expression to assign to the extra column: keys with a value are added or replaced, keys set to
    None are removed. Stored {"a": 1, "b": 2} with changes {"b": None, "c": 3} becomes {"a": 1, "c": 3}.

    The merge runs inside the UPDATE, so two requests changing different keys at the same time keep both.
    """
    kept = drop_null_keys(changes)
    removed = [key for key, value in changes.items() if value is None]
    return column.op("||")(literal(kept, JSONB)).op("-")(literal(removed, ARRAY(Text)))
