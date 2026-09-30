"""
Structured logging configuration for NetMind.

Uses structlog with JSON output in production and colored console output
in development. Every log event includes a timestamp, level, service,
and trace context fields.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from netmind.core.config import get_settings


def _add_service_name(
    logger: logging.Logger,  # noqa: ARG001
    method_name: str,  # noqa: ARG001
    event_dict: EventDict,
) -> EventDict:
    """Inject static service name into every log record."""
    event_dict["service"] = "netmind-api"
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog for the application.

    In development: timestamped, colored console output.
    In production: JSON output suitable for log aggregators (Loki, CloudWatch, etc.).
    """
    settings = get_settings()
    is_dev = settings.is_development

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _add_service_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if is_dev:
        processors: list[Processor] = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.getLevelName(settings.log_level),
    )


def get_logger(name: str) -> Any:
    """Return a bound structlog logger for the given name."""
    return structlog.get_logger(name)
