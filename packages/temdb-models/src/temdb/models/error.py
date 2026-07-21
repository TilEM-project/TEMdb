"""API error response models."""

from typing import Any

from pydantic import Field

from .base import TEMDBModel


class APIErrorResponse(TEMDBModel):
    """Standard structure for API error responses."""

    detail: str = Field(..., description="Human-readable description of the error.")
    error_code: str | None = Field(None, description="Optional machine-readable error code.")
    context: dict[str, Any] | None = Field(
        None,
        description="Optional additional context about the error.",
    )
