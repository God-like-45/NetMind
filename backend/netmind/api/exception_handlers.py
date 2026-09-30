"""
Global exception handler middleware.

Maps NetMind typed exceptions to consistent JSON error responses.
No implementation detail leaks to clients in production.
"""

from __future__ import annotations

import traceback
import uuid
from http import HTTPStatus

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from netmind.core.exceptions import NetMindError
from netmind.core.logging import get_logger

logger = get_logger(__name__)


def _error_response(
    status_code: int,
    error_code: str,
    message: str,
    request_id: str,
    detail: str | None = None,
) -> JSONResponse:
    """Construct a consistent error JSON response."""
    body: dict[str, object] = {
        "error_code": error_code,
        "message": message,
        "request_id": request_id,
    }
    if detail:
        body["detail"] = detail
    return JSONResponse(status_code=status_code, content=body)


async def netmind_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all NetMind application exceptions."""
    request_id = str(uuid.uuid4())[:8]

    if isinstance(exc, NetMindError):
        logger.warning(
            "Application error",
            error_code=exc.error_code,
            message=exc.message,
            request_id=request_id,
            path=str(request.url),
        )
        return _error_response(
            status_code=exc.status_code,
            error_code=exc.error_code,
            message=exc.message,
            request_id=request_id,
            detail=exc.detail,
        )

    # Unhandled exception - log full traceback, return generic 500
    logger.error(
        "Unhandled exception",
        request_id=request_id,
        path=str(request.url),
        exc_info=traceback.format_exc(),
    )
    return _error_response(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred. The error has been logged.",
        request_id=request_id,
    )


async def validation_exception_handler(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    """Handle Pydantic v2 validation errors with structured output."""
    request_id = str(uuid.uuid4())[:8]
    logger.info(
        "Request validation failed",
        request_id=request_id,
        path=str(request.url),
        errors=exc.errors(),
    )
    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "request_id": request_id,
            "errors": exc.errors(include_url=False),
        },
    )
