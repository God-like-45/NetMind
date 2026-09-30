"""
Test suite root configuration.

conftest.py is automatically loaded by pytest before any tests run.
Provides shared fixtures available to all test modules.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

# ─── Override environment before any imports that read settings ──────────────
# These must be set before the application creates settings objects.
os.environ.setdefault("POSTGRES_PASSWORD", "test_password")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_DB", "netmind_test")
os.environ.setdefault("POSTGRES_USER", "netmind_test")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_for_testing_only_not_for_production")
os.environ.setdefault("APP_ENV", "development")


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    """
    Clear lru_cache on settings functions before each test.

    Ensures environment variable changes between tests take effect.
    """
    from netmind.core.config import (
        get_jwt_settings,
        get_kafka_settings,
        get_mlflow_settings,
        get_ollama_settings,
        get_postgres_settings,
        get_redis_settings,
        get_settings,
    )

    get_settings.cache_clear()
    get_postgres_settings.cache_clear()
    get_redis_settings.cache_clear()
    get_kafka_settings.cache_clear()
    get_jwt_settings.cache_clear()
    get_ollama_settings.cache_clear()
    get_mlflow_settings.cache_clear()
