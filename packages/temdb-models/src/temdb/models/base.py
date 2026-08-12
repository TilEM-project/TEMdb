from pydantic import BaseModel, ConfigDict


class TEMDBModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TEMDBResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
