from functools import cache
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator


class TEMDBModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TEMDBResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class TEMDBRecord(TEMDBModel):
    """A stored record that also carries free-form fields outside its schema."""

    extra: dict[str, Any] | None = Field(
        None, description="Free-form fields outside the schema; an update merges keys and null removes one"
    )

    @field_validator("extra")
    @classmethod
    def extra_is_at_most_32_levels_deep(cls, extra):
        """Reject data in the 'extra' field being deeper than 32 levels."""
        levels = [(extra, 1)] if extra else []
        while levels:
            value, depth = levels.pop()
            if depth > 32:
                raise ValueError("extra is nested more than 32 levels deep")
            children = value.values() if isinstance(value, dict) else value
            levels.extend((child, depth + 1) for child in children if isinstance(child, dict | list))
        return extra

    @model_validator(mode="after")
    def extra_keys_are_not_fields(self):
        taken = sorted(set(self.extra or {}) & record_field_names(type(self).__module__))
        if taken:
            raise ValueError(f"extra keys {taken} are fields of this record; set them directly")
        return self


def record_classes(cls: type) -> list[type]:
    return [cls, *(sub for child in cls.__subclasses__() for sub in record_classes(child))]


@cache
def record_field_names(module: str) -> frozenset[str]:
    """Return the field names and aliases of all record models in one file, e.g. every Block* model in block.py.

    Assumes each file holds one resource's models, so Create, Update and Response share the same reserved names.
    """
    names = set()
    for cls in record_classes(TEMDBRecord):
        if cls.__module__ != module:
            continue
        for name, field in cls.model_fields.items():
            aliases = field.validation_alias.choices if isinstance(field.validation_alias, AliasChoices) else []
            names.update(
                alias for alias in (name, field.alias, field.validation_alias, *aliases) if isinstance(alias, str)
            )
    return frozenset(names)
