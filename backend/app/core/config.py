"""
Application configuration.
All values are loaded from environment variables.
No secrets are hardcoded here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = "BrandShield AI"
    app_version: str = "0.1.0"
    app_env: str = "development"
    app_debug: bool = True

    # ── Database ─────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://brandshield:brandshield_dev_password@localhost:5432/brandshield"
    )

    # ── AI / LLM ─────────────────────────────────────────────
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    # Configured provider: "openai" or "none" (all other values use fallback)
    # If empty or "none", the template fallback is always used.
    ai_provider: str = ""
    ai_model: str = "gpt-4o-mini"
    ai_api_key: str = ""
    # Max tokens for investigation responses (keep short for speed)
    ai_max_tokens: int = 800
    # Timeout in seconds for LLM calls
    ai_timeout_seconds: int = 15

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ── Demo ─────────────────────────────────────────────────
    demo_mode: bool = True


# Singleton — import this everywhere
settings = Settings()
