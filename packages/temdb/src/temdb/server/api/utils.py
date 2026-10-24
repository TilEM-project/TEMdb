from typing import Any

from sqlalchemy import Text, literal
from sqlalchemy.dialects.postgresql import ARRAY, JSONB


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
