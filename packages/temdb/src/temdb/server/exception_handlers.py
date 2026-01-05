import logging

from beanie.exceptions import DocumentNotFound
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError
from temdb.models import APIErrorResponse

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


async def duplicate_key_exception_handler(request: Request, exc: DuplicateKeyError):
    """Handles MongoDB duplicate key errors (returns 409 Conflict)."""
    conflicting_key = "unknown_field"
    conflicting_value = "unknown_value"
    try:
        details = exc.details
        if details and "keyPattern" in details and "keyValue" in details:
            conflicting_key = list(details["keyPattern"].keys())[0]
            conflicting_value = details["keyValue"].get(conflicting_key, "unknown")
    except Exception as parse_exc:
        logger.warning(f"Could not parse DuplicateKeyError details: {parse_exc}")

    error_content = APIErrorResponse(
        detail=(
            "Resource creation failed due to a conflict. A resource with the same "
            f"unique identifier ('{conflicting_key}') already exists."
        ),
        error_code="DUPLICATE_RESOURCE",
        context={
            "conflicting_field": conflicting_key,
            "conflicting_value": str(conflicting_value),
        },
    )
    logger.warning(f"DuplicateKeyError on {request.url}: {error_content.detail}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_content.model_dump(exclude_none=True),
    )


async def document_not_found_exception_handler(request: Request, exc: DocumentNotFound):
    """Handles Beanie DocumentNotFound errors (returns 404 Not Found)."""
    error_content = APIErrorResponse(detail="The requested resource was not found.", error_code="RESOURCE_NOT_FOUND")
    logger.info(f"DocumentNotFound on {request.url}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_content.model_dump(exclude_none=True),
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
    app.add_exception_handler(DuplicateKeyError, duplicate_key_exception_handler)
    app.add_exception_handler(DocumentNotFound, document_not_found_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(BaseError, business_logic_exception_handler)

    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info("Registered custom exception handlers.")
