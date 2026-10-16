import logging
from http import HTTPStatus

from asyncpg.exceptions import (
    CharacterNotInRepertoireError,
    ForeignKeyViolationError,
    InvalidTextRepresentationError,
    UniqueViolationError,
    UntranslatableCharacterError,
)
from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError, IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from temdb.models import APIErrorResponse
from temdb.server.config import is_debug_traceback_enabled

logger = logging.getLogger(__name__)


class BaseError(Exception):
    """Base class for application errors."""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str | None = None,
        context: dict | None = None,
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__.upper()
        self.context = context
        super().__init__(detail)


class ResourceInUseError(BaseError):
    """Raised when trying to delete a resource that's still linked."""

    def __init__(self, resource_type: str, resource_id: str, context: dict | None = None):
        detail = (
            f"{resource_type} '{resource_id}' cannot be deleted because "
            "it is still in use or linked by other resources."
        )
        super().__init__(
            detail,
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_IN_USE",
            context=context,
        )


async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handles Pydantic ValidationErrors (returns 422 Unprocessable Entity)."""
    error_content = APIErrorResponse(
        detail="Request validation failed. Please check the input data.",
        error_code="VALIDATION_ERROR",
        context={"errors": jsonable_encoder(exc.errors())},
    )
    logger.warning(f"ValidationError on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error_content.model_dump(exclude_none=True),
    )


async def business_logic_exception_handler(request: Request, exc: BaseError):
    """Handles custom application-specific errors."""
    error_content = APIErrorResponse(detail=exc.detail, error_code=exc.error_code, context=exc.context)
    logger.warning(f"{exc.__class__.__name__} on {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=error_content.model_dump(exclude_none=True),
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handles any other unexpected exceptions (returns 500 Internal Server Error)."""
    logger.exception(f"Unhandled exception during request to {request.url}", exc_info=exc)
    if is_debug_traceback_enabled():
        raise exc

    error_content = APIErrorResponse(
        detail="An unexpected internal server error occurred. Please contact the administrator.",
        error_code="INTERNAL_SERVER_ERROR",
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_content.model_dump(exclude_none=True),
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Wraps every HTTPException in APIErrorResponse; error_code is the status name, e.g. NOT_FOUND."""
    http_status = HTTPStatus(exc.status_code)
    if isinstance(exc.detail, str):
        error_content = APIErrorResponse(detail=exc.detail, error_code=http_status.name)
    else:
        error_content = APIErrorResponse(
            detail=http_status.phrase, error_code=http_status.name, context={"detail": jsonable_encoder(exc.detail)}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_content.model_dump(exclude_none=True),
        headers=exc.headers,
    )


async def integrity_exception_handler(request: Request, exc: IntegrityError):
    """Foreign-key and unique violations are a 409 naming the table; other violations stay 500."""
    postgres_error = exc.driver_exception
    if isinstance(postgres_error, ForeignKeyViolationError):
        error_code = "FOREIGN_KEY_VIOLATION"
    elif isinstance(postgres_error, UniqueViolationError):
        error_code = "UNIQUE_VIOLATION"
    else:
        return await generic_exception_handler(request, exc)
    error_content = APIErrorResponse(
        detail=postgres_error.detail,
        error_code=error_code,
        context={"table": postgres_error.table_name, "constraint": postgres_error.constraint_name},
    )
    logger.warning(f"{error_code} on {request.url}: {error_content.detail}")
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=error_content.model_dump(exclude_none=True))


async def database_error_handler(request: Request, exc: DBAPIError):
    """Return 422 when a string contains a NUL character or a lone UTF-16 surrogate, which Postgres rejects.

    Every other database error is passed to the generic 500 handler.
    """
    postgres_error = exc.driver_exception
    unstorable = CharacterNotInRepertoireError | UntranslatableCharacterError | InvalidTextRepresentationError
    if not (isinstance(postgres_error, unstorable) or isinstance(postgres_error.__cause__, UnicodeEncodeError)):
        return await generic_exception_handler(request, exc)
    error_content = APIErrorResponse(detail=f"Text cannot be stored: {postgres_error}", error_code="VALIDATION_ERROR")
    logger.warning(f"Unstorable text on {request.url}: {postgres_error}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content=error_content.model_dump(exclude_none=True)
    )


async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles FastAPI RequestValidationError (returns 422 Unprocessable Entity)."""
    error_content = APIErrorResponse(
        detail="Request validation failed. Please check the input data.",
        error_code="VALIDATION_ERROR",
        context={"errors": jsonable_encoder(exc.errors())},
    )
    logger.warning(f"RequestValidationError on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=error_content.model_dump(exclude_none=True),
    )


def register_exception_handlers(app):
    """Registers all defined exception handlers with the FastAPI app."""
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(BaseError, business_logic_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_exception_handler)
    app.add_exception_handler(DBAPIError, database_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info("Registered custom exception handlers.")
