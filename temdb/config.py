from pydantic_settings import BaseSettings


class Config(BaseSettings):
    MONGODB_URL: str = "mongodb://localhost:27017/"
    DB_NAME: str = "temdb"

    class Config:
        env_prefix = "TEMDB_"
        env_file = ".env"


config = Config()
