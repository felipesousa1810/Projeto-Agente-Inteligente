"""Application Settings - Pydantic Settings for environment configuration."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings are loaded from .env file or environment variables.
    Validation is automatic via Pydantic.
    """

    # LLM Settings
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 256
    llm_timeout: int = 10

    # Database (Supabase)
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # Evolution API (WhatsApp)
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = ""
    evolution_instance_name: str = "default"

    # Observability
    jaeger_endpoint: str = "http://localhost:14268/api/traces"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # Redis (Idempotency)
    redis_url: str = "redis://localhost:6379"

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    api_port: int = 8000
    api_host: str = "0.0.0.0"

    # Feature Flags
    enable_tracing: bool = True
    enable_metrics: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses lru_cache for performance - settings are loaded once.
    """
    return Settings()  # type: ignore[call-arg]
