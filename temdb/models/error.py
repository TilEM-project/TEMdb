from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class APIErrorResponse(BaseModel):
    """Standard structure for API error responses."""

    detail: str = Field(..., description="Human-readable description of the error.")
    error_code: Optional[str] = Field(
        None, description="Optional machine-readable error code."
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional additional context about the error (e.g., conflicting field/value).",
    )
