from datetime import datetime

from sqlalchemy import DateTime, MetaData, func, inspect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )


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
