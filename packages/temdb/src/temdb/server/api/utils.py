from functools import wraps
from inspect import isawaitable
from typing import Any

from sqlalchemy import inspect as sa_inspect


def _orm_to_dict_with_extra(obj: Any):
    state = sa_inspect(obj, raiseerr=False)
    if state is None or not hasattr(state, "mapper"):
        return obj
    raw = {attr.key: getattr(obj, attr.key) for attr in state.mapper.column_attrs if attr.key != "extra"}
    extra = dict(getattr(obj, "extra", {}) or {})
    extra.update(raw)
    return extra


def _include_extra(value: Any):
    if isinstance(value, list):
        return [_include_extra(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_include_extra(item) for item in value)
    if isinstance(value, set):
        return [_include_extra(item) for item in value]
    if isinstance(value, dict):
        return {key: _include_extra(item) for key, item in value.items()}
    return _orm_to_dict_with_extra(value)


def include_extra(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if isawaitable(result):
            result = await result
        return _include_extra(result)

    return wrapper


def model_dump_with_extra(obj: Any, *, extra_source: Any = None, **kwargs):
    if obj is None:
        return None
    payload = obj.model_dump(**kwargs)
    if isinstance(payload, dict):
        source = obj if extra_source is None else extra_source
        payload.update(getattr(source, "extra", {}) or {})
    return payload
