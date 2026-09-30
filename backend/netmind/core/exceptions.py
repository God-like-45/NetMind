"""
Custom exception hierarchy for NetMind.

Using a typed exception hierarchy allows middleware to handle errors
consistently without inspecting string messages.
"""

from __future__ import annotations

from http import HTTPStatus


class NetMindError(Exception):
    """Base exception for all NetMind errors."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


# ─── Authentication / Authorization ──────────────────────────────────────────


class AuthenticationError(NetMindError):
    """Raised when credentials are invalid or missing."""

    status_code = HTTPStatus.UNAUTHORIZED
    error_code = "AUTHENTICATION_FAILED"


class AuthorizationError(NetMindError):
    """Raised when a user lacks permission for an action."""

    status_code = HTTPStatus.FORBIDDEN
    error_code = "AUTHORIZATION_FAILED"


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""

    error_code = "TOKEN_EXPIRED"


# ─── Resource Errors ─────────────────────────────────────────────────────────


class NotFoundError(NetMindError):
    """Raised when a requested resource does not exist."""

    status_code = HTTPStatus.NOT_FOUND
    error_code = "NOT_FOUND"


class ConflictError(NetMindError):
    """Raised when a resource conflict occurs (e.g., duplicate key)."""

    status_code = HTTPStatus.CONFLICT
    error_code = "CONFLICT"


# ─── Validation Errors ───────────────────────────────────────────────────────


class ValidationError(NetMindError):
    """Raised when input data fails business-level validation."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


# ─── Infrastructure Errors ───────────────────────────────────────────────────


class DatabaseError(NetMindError):
    """Raised when a database operation fails."""

    error_code = "DATABASE_ERROR"


class KafkaError(NetMindError):
    """Raised when a Kafka operation fails."""

    error_code = "KAFKA_ERROR"


class CacheError(NetMindError):
    """Raised when a Redis operation fails."""

    error_code = "CACHE_ERROR"


# ─── ML / Agent Errors ───────────────────────────────────────────────────────


class ModelNotReadyError(NetMindError):
    """Raised when an ML model is not yet trained or loaded."""

    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    error_code = "MODEL_NOT_READY"


class AgentError(NetMindError):
    """Raised when an agent execution fails."""

    error_code = "AGENT_ERROR"


class PromptInjectionError(NetMindError):
    """Raised when potential prompt injection is detected in user input."""

    status_code = HTTPStatus.BAD_REQUEST
    error_code = "PROMPT_INJECTION_DETECTED"


# ─── Rate Limiting ───────────────────────────────────────────────────────────


class RateLimitError(NetMindError):
    """Raised when a client exceeds the configured rate limit."""

    status_code = HTTPStatus.TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"
