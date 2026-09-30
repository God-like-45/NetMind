"""
Application configuration loaded from environment variables.

Uses pydantic-settings for validation and type coercion.
All secrets MUST be supplied via environment variables or a .env file.
No secrets are hardcoded here.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseSettings):
    """PostgreSQL connection settings."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    host: str = "localhost"
    port: int = 5432
    db: str = "netmind"
    user: str = "netmind"
    password: SecretStr = Field(default=..., description="PostgreSQL password - required")

    @property
    def async_dsn(self) -> str:
        """Return asyncpg-compatible DSN."""
        return (
            f"postgresql+asyncpg://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.db}"
        )

    @property
    def sync_dsn(self) -> str:
        """Return psycopg2-compatible DSN (used by Alembic)."""
        return (
            f"postgresql+psycopg2://{self.user}:{self.password.get_secret_value()}"
            f"@{self.host}:{self.port}/{self.db}"
        )


class RedisSettings(BaseSettings):
    """Redis connection settings."""

    model_config = SettingsConfigDict(env_prefix="REDIS_", extra="ignore")

    host: str = "localhost"
    port: int = 6379
    password: SecretStr | None = None

    @property
    def url(self) -> str:
        """Return redis:// URL."""
        if self.password:
            return f"redis://:{self.password.get_secret_value()}@{self.host}:{self.port}/0"
        return f"redis://{self.host}:{self.port}/0"


class KafkaSettings(BaseSettings):
    """Kafka connection and topic settings."""

    model_config = SettingsConfigDict(env_prefix="KAFKA_", extra="ignore")

    bootstrap_servers: str = "localhost:9092"

    # Topic names
    topic_telemetry: str = "netmind.telemetry"
    topic_alarms: str = "netmind.alarms"
    topic_topology: str = "netmind.topology"
    topic_config_changes: str = "netmind.config_changes"
    topic_anomalies: str = "netmind.anomalies"
    topic_incidents: str = "netmind.incidents"

    @property
    def all_topics(self) -> list[str]:
        """Return all topic names for admin client."""
        return [
            self.topic_telemetry,
            self.topic_alarms,
            self.topic_topology,
            self.topic_config_changes,
            self.topic_anomalies,
            self.topic_incidents,
        ]


class JWTSettings(BaseSettings):
    """JWT authentication settings."""

    model_config = SettingsConfigDict(env_prefix="JWT_", extra="ignore")

    secret_key: SecretStr = Field(default=..., description="JWT signing secret - required")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


class OllamaSettings(BaseSettings):
    """Ollama LLM backend settings."""

    model_config = SettingsConfigDict(env_prefix="OLLAMA_", extra="ignore")

    host: str = "http://localhost:11434"
    model: str = "llama3.2:3b"
    request_timeout: float = 120.0


class MLflowSettings(BaseSettings):
    """MLflow tracking settings."""

    model_config = SettingsConfigDict(env_prefix="MLFLOW_", extra="ignore")

    tracking_uri: str = "http://localhost:5000"
    experiment_name: str = "netmind-anomaly-detection"


class Settings(BaseSettings):
    """
    Root application settings.

    Reads from environment variables and .env file.
    Nested settings objects are composed manually to allow env_prefix isolation.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ─────────────────────────────────────────────────────────
    app_env: Literal["development", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    api_cors_origins: list[str] | str = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins",
    )

    # ─── Rate limiting ───────────────────────────────────────────────────────
    rate_limit_default: str = "100/minute"
    rate_limit_agent: str = "10/minute"

    @field_validator("api_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Accept comma-separated string or a list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_development(self) -> bool:
        """True when running in development mode."""
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return cached application settings.

    Uses lru_cache so environment is only parsed once per process.
    In tests, call get_settings.cache_clear() to reset.
    """
    return Settings()


@lru_cache(maxsize=1)
def get_postgres_settings() -> PostgresSettings:
    """Return cached PostgreSQL settings."""
    return PostgresSettings()


@lru_cache(maxsize=1)
def get_redis_settings() -> RedisSettings:
    """Return cached Redis settings."""
    return RedisSettings()


@lru_cache(maxsize=1)
def get_kafka_settings() -> KafkaSettings:
    """Return cached Kafka settings."""
    return KafkaSettings()


@lru_cache(maxsize=1)
def get_jwt_settings() -> JWTSettings:
    """Return cached JWT settings."""
    return JWTSettings()


@lru_cache(maxsize=1)
def get_ollama_settings() -> OllamaSettings:
    """Return cached Ollama settings."""
    return OllamaSettings()


@lru_cache(maxsize=1)
def get_mlflow_settings() -> MLflowSettings:
    """Return cached MLflow settings."""
    return MLflowSettings()
