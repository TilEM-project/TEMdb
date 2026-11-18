import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from temdb.models import StorageDefault


class BaseConfig(BaseSettings):
    app_name: str = "TEMDB"
    database_url: str | None = None
    default_storage: StorageDefault | None = None
    image_lookup_concurrency: int = Field(10, ge=1, description="How many images to look up at once")
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="allow",
    )


class DevConfig(BaseConfig):
    debug: bool = True
    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file="dev.env",
        extra="allow",
    )


class ProdConfig(BaseConfig):
    debug: bool = False

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=".env",
        extra="allow",
    )


def get_config():
    env = os.getenv("TEMDB_ENV", "dev").lower()
    if env == "prod":
        return ProdConfig()
    return DevConfig()


def is_debug_traceback_enabled() -> bool:
    return os.getenv("DEBUG", "").strip().lower() == "true"


config = get_config()
