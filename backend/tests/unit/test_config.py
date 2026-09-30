"""Unit tests for application configuration."""

from __future__ import annotations

import os

import pytest

from netmind.core.config import (
    KafkaSettings,
    PostgresSettings,
    RedisSettings,
    Settings,
    get_settings,
)


class TestPostgresSettings:
    """Test PostgreSQL settings parsing and DSN construction."""

    def test_async_dsn_format(self) -> None:
        """async_dsn must use asyncpg scheme."""
        settings = PostgresSettings(
            host="db-host",
            port=5432,
            db="mydb",
            user="myuser",
            password="mypass",  # type: ignore[arg-type]
        )
        dsn = settings.async_dsn
        assert dsn.startswith("postgresql+asyncpg://")
        assert "db-host:5432" in dsn
        assert "mydb" in dsn
        # Password must appear in DSN (it needs to for connection to work)
        assert "mypass" in dsn

    def test_sync_dsn_format(self) -> None:
        """sync_dsn must use psycopg2 scheme for Alembic."""
        settings = PostgresSettings(
            host="db-host",
            port=5432,
            db="mydb",
            user="myuser",
            password="mypass",  # type: ignore[arg-type]
        )
        dsn = settings.sync_dsn
        assert dsn.startswith("postgresql+psycopg2://")

    def test_password_is_secret(self) -> None:
        """Password must be a SecretStr - not exposed via str()."""
        settings = PostgresSettings(
            host="localhost",
            db="test",
            user="test",
            password="super_secret",  # type: ignore[arg-type]
        )
        # SecretStr should not reveal the value in repr/str
        assert "super_secret" not in str(settings.password)
        assert "super_secret" not in repr(settings.password)
        # But get_secret_value() must work
        assert settings.password.get_secret_value() == "super_secret"


class TestRedisSettings:
    """Test Redis settings and URL construction."""

    def test_url_without_password(self) -> None:
        """URL without password should not include auth section."""
        settings = RedisSettings(host="redis-host", port=6379, password=None)
        url = settings.url
        assert url == "redis://redis-host:6379/0"
        assert "@" not in url

    def test_url_with_password(self) -> None:
        """URL with password must include auth credentials."""
        settings = RedisSettings(
            host="redis-host",
            port=6379,
            password="redispass",  # type: ignore[arg-type]
        )
        url = settings.url
        assert "redispass" in url
        assert "@redis-host" in url


class TestKafkaSettings:
    """Test Kafka settings."""

    def test_all_topics_returns_six_topics(self) -> None:
        """all_topics must include all six NetMind topic names."""
        settings = KafkaSettings(bootstrap_servers="kafka:9092")
        topics = settings.all_topics
        assert len(topics) == 6
        assert all(t.startswith("netmind.") for t in topics)

    def test_default_bootstrap_servers(self) -> None:
        """Default bootstrap servers should match docker-compose service name."""
        settings = KafkaSettings()
        assert "9092" in settings.bootstrap_servers


class TestSettings:
    """Test root application settings."""

    def test_default_environment_is_development(self) -> None:
        """Default app_env should be 'development'."""
        settings = Settings(
            postgres_password="x",  # type: ignore[call-arg]
            jwt_secret_key="x",  # type: ignore[call-arg]
        )
        assert settings.app_env == "development"
        assert settings.is_development is True

    def test_cors_origins_parsed_from_comma_string(self) -> None:
        """CORS origins should accept a comma-separated string."""
        settings = Settings(
            api_cors_origins="http://localhost:3000,http://localhost:4000",  # type: ignore[call-arg]
            postgres_password="x",  # type: ignore[call-arg]
            jwt_secret_key="x",  # type: ignore[call-arg]
        )
        assert len(settings.api_cors_origins) == 2

    def test_get_settings_returns_cached_instance(self) -> None:
        """get_settings() must return the same instance on multiple calls."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_log_level_valid_values(self) -> None:
        """log_level must reject invalid values."""
        with pytest.raises(Exception):  # pydantic ValidationError
            Settings(
                log_level="INVALID",  # type: ignore[call-arg]
                postgres_password="x",  # type: ignore[call-arg]
                jwt_secret_key="x",  # type: ignore[call-arg]
            )
