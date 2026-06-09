import logging

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

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
        context={"errors": exc.errors()},
    )
    logger.warning(f"ValidationError on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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


async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles FastAPI RequestValidationError (returns 422 Unprocessable Entity)."""
    error_content = APIErrorResponse(
        detail="Request validation failed. Please check the input data.",
        error_code="VALIDATION_ERROR",
        context={"errors": exc.errors()},
    )
    logger.warning(f"RequestValidationError on {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_content.model_dump(exclude_none=True),
    )


def register_exception_handlers(app):
    """Registers all defined exception handlers with the FastAPI app."""
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(BaseError, business_logic_exception_handler)

    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info("Registered custom exception handlers.")
