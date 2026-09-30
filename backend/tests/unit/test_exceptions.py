"""Unit tests for exception hierarchy."""

from __future__ import annotations

from http import HTTPStatus

import pytest

from netmind.core.exceptions import (
    AgentError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    NetMindError,
    NotFoundError,
    PromptInjectionError,
    RateLimitError,
    TokenExpiredError,
    ValidationError,
)


class TestExceptionHierarchy:
    """Verify exception hierarchy and status codes."""

    def test_all_custom_exceptions_inherit_from_netmind_error(self) -> None:
        """All custom exceptions must inherit from NetMindError."""
        custom_exceptions = [
            AuthenticationError,
            AuthorizationError,
            TokenExpiredError,
            NotFoundError,
            ValidationError,
            DatabaseError,
            AgentError,
            PromptInjectionError,
            RateLimitError,
        ]
        for exc_class in custom_exceptions:
            assert issubclass(exc_class, NetMindError), (
                f"{exc_class.__name__} must inherit from NetMindError"
            )

    def test_authentication_error_is_401(self) -> None:
        assert AuthenticationError.status_code == HTTPStatus.UNAUTHORIZED

    def test_authorization_error_is_403(self) -> None:
        assert AuthorizationError.status_code == HTTPStatus.FORBIDDEN

    def test_not_found_error_is_404(self) -> None:
        assert NotFoundError.status_code == HTTPStatus.NOT_FOUND

    def test_rate_limit_error_is_429(self) -> None:
        assert RateLimitError.status_code == HTTPStatus.TOO_MANY_REQUESTS

    def test_token_expired_inherits_from_authentication_error(self) -> None:
        assert issubclass(TokenExpiredError, AuthenticationError)

    def test_exception_carries_message_and_detail(self) -> None:
        exc = NotFoundError(message="Incident not found", detail="ID: abc-123")
        assert exc.message == "Incident not found"
        assert exc.detail == "ID: abc-123"
        assert str(exc) == "Incident not found"

    def test_exception_error_codes_are_unique(self) -> None:
        """Each exception class should have a unique error_code."""
        exc_classes = [
            AuthenticationError,
            AuthorizationError,
            TokenExpiredError,
            NotFoundError,
            ValidationError,
            DatabaseError,
            AgentError,
            PromptInjectionError,
            RateLimitError,
        ]
        codes = [cls.error_code for cls in exc_classes]
        assert len(codes) == len(set(codes)), "Duplicate error codes found"

    def test_prompt_injection_is_400(self) -> None:
        assert PromptInjectionError.status_code == HTTPStatus.BAD_REQUEST

    def test_netmind_error_default_500(self) -> None:
        exc = NetMindError("base error")
        assert exc.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
