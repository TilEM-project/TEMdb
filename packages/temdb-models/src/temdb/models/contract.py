from temdb.models.base import TEMDBModel


class Contract(TEMDBModel):
    """API and package versions used to verify client-server compatibility."""

    api: str
    server_version: str
    models_version: str
