from pydantic import BaseModel, ConfigDict


class TEMDBModel(BaseModel):
    model_config = ConfigDict(extra="allow")

    def model_dump(self, *args, extra: bool = True, include=None, **kwargs):
        if not extra:
            if include is not None and not isinstance(include, (list, set, tuple)):
                raise ValueError("If extra=False include must be a list, set, or tuple.")
            include_values = set(include or [])
            include_values.update(type(self).model_fields.keys())
            return super().model_dump(*args, include=include_values, **kwargs)
        return super().model_dump(*args, include=include, **kwargs)


class TEMDBResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="allow")
