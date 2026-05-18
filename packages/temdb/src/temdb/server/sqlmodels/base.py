from sqlalchemy import inspect
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class ModelDumpMixin:
    def model_dump(self, **kwargs):
        exclude_none = kwargs.get("exclude_none", False)
        payload = {}
        for attr in inspect(self.__class__).column_attrs:
            value = getattr(self, attr.key)
            if exclude_none and value is None:
                continue
            payload[attr.key] = value
        return payload
