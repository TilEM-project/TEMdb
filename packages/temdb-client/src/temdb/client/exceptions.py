from httpx import HTTPStatusError


def _format_validation_errors(errors) -> str:
    if not isinstance(errors, list):
        return ""
    rendered = []
    for error in errors:
        if not isinstance(error, dict):
            continue
        loc = ".".join(str(part) for part in error.get("loc", []))
        msg = error.get("msg", "")
        rendered.append(f"{loc}: {msg}" if loc else str(msg))
    return "; ".join(part for part in rendered if part)


class TEMdbError(Exception):
    """Base exception for TEMdb errors."""

    pass


class TEMdbClientError(TEMdbError):
    """Base exception for TEMdb client errors."""

    pass


class TEMdbServerError(TEMdbError):
    """Base exception for TEMdb server errors."""

    NAME = "TEMdb server error"

    def __init__(
        self,
        message: str,
        code: int,
        traceback: str | None = None,
        error_code: str | None = None,
        context: dict | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.traceback = traceback
        self.error_code = error_code
        self.context = context or {}

    @classmethod
    def from_httpx_status_error(cls, httpx_error):
        assert isinstance(httpx_error, HTTPStatusError)
        code = httpx_error.response.status_code
        exception = cls._get_exception(code)
        try:
            payload = httpx_error.response.json()
        except Exception:
            payload = None
        if not isinstance(payload, dict):
            payload = {"detail": httpx_error.response.text}
        context = payload.get("context")
        if not isinstance(context, dict):
            context = {}
        message = f"{httpx_error.request.url}: {payload.get('detail', exception.NAME)}"
        errors = _format_validation_errors(context.get("errors"))
        if errors:
            message = f"{message} [{errors}]"
        return exception(
            message,
            code,
            context.get("traceback"),
            error_code=payload.get("error_code"),
            context=context,
        )

    @classmethod
    def _get_exception(cls, code):
        error_map = {
            400: TEMdbBadRequestError,
            404: TEMdbNotFoundError,
            409: TEMdbConflictError,
            422: TEMdbUnprocessableError,
            500: TEMdbInternalError,
            501: TEMdbNotImplementedError,
        }
        return error_map.get(code, cls)


class TEMdbBadRequestError(TEMdbServerError):
    """Bad request error."""

    NAME = "Bad request"


class TEMdbNotFoundError(TEMdbServerError):
    """Resource not found."""

    NAME = "Not found"


class TEMdbConflictError(TEMdbServerError):
    """Conflict error."""

    NAME = "Conflict"


class TEMdbUnprocessableError(TEMdbServerError):
    """Server unprocessable error."""

    NAME = "Unprocessable"


class TEMdbInternalError(TEMdbServerError):
    """Internal server error."""

    NAME = "Internal Error"


class TEMdbNotImplementedError(TEMdbServerError):
    """Not implemented error."""

    NAME = "Not implemented"
