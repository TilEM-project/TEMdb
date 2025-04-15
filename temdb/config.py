import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    app_name: str = "TEMDB"
    mongodb_uri: str
    mongodb_name: str
    max_batch_size: int = 5000
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


config = get_config()
