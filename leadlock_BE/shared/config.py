"""
LeadLock AI — Application Configuration
Centralized Pydantic BaseSettings for all environment variables.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of truth for all application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://leadlock:leadlock_secret@localhost:5432/leadlock"
    database_echo: bool = False

    # ── Redis ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── AI / LLM ─────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str | None = None

    # ── OpenWA ───────────────────────────────────────────────────────────
    openwa_base_url: str = "http://localhost:2785"
    openwa_api_key: str = ""
    openwa_default_session_id: str = "default"

    # ── Edge Worker ──────────────────────────────────────────────────────
    edge_worker_host: str = "0.0.0.0"
    edge_worker_port: int = 8001

    # ── Core Service ─────────────────────────────────────────────────────
    core_service_host: str = "0.0.0.0"
    core_service_port: int = 8000

    # ── Security ─────────────────────────────────────────────────────────
    secret_key: str = "change-this-to-a-random-secret-key-in-production"
    api_key: str = "leadlock-dev-api-key"

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # ── Logging ──────────────────────────────────────────────────────────
    log_level: str = "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Singleton instance — import this everywhere
settings = Settings()
