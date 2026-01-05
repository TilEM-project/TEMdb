class TEMdbClientError(Exception):
    """Base exception for TEMdb client errors."""

    pass


class NotFoundError(TEMdbClientError):
    """Resource not found."""

    pass
