"""
prism_core/config/settings.py

Centralised environment config via pydantic-settings.
All runtime secrets and service URLs come from environment variables.
No secrets are ever hardcoded in this file or anywhere in app code.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Environment ─────────────────────────────────────────────────────────────
    environment: str = "development"

    # ── Database ─────────────────────────────────────────────────────────────────
    database_url: PostgresDsn  # required — comes from Render env group or .env

    # ── Auth ──────────────────────────────────────────────────────────────────────
    secret_key: SecretStr  # required — Render generates this
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 8

    # ── External AI / ML ──────────────────────────────────────────────────────────
    gemini_key: SecretStr | None = None
    sarvam_key: SecretStr | None = None

    # ── Mail provider (Gmail OAuth2, Resend, SMTP, Postmark, Simulated) ─────────
    mail_provider: str = "simulated"  # "simulated" | "gmail" | "resend" | "smtp" | "postmark"
    mail_provider_key: SecretStr | None = None
    mail_from: str = "noreply@prism.app"

    # Gmail OAuth 2.0 Credentials (app-level OAuth with refresh token)
    gmail_client_id: SecretStr | None = None
    gmail_client_secret: SecretStr | None = None
    gmail_refresh_token: SecretStr | None = None
    gmail_user_email: str | None = None  # Explicit sender address if different from mail_from

    # Explicit SMTP alternative (Gmail App Password / custom relay)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = True

    # ── Slack webhook (serious alerts) ────────────────────────────────────────────
    slack_webhook: str | None = None

    # ── Render Workflows ──────────────────────────────────────────────────────────
    render_api_key: SecretStr | None = None
    render_service_id: str | None = None  # prism-workflows service id

    # ── Model paths (baked into Docker image at /models/) ─────────────────────────
    model_dir: Path = Path("/models/multilingual-e5-small")

    # ── Config paths ─────────────────────────────────────────────────────────────
    config_dir: Path = Path(__file__).parent
    thresholds_path: Path = Path(__file__).parent / "thresholds.yaml"
    lexicon_path: Path = Path(__file__).parent / "lexicons" / "sentiment_lexicon.yaml"

    # ── Feature flags ─────────────────────────────────────────────────────────────
    enable_vision: bool = True          # set False to skip Gemini vision (cost saving)
    enable_stt: bool = True             # set False to skip audio STT
    enable_sarvam: bool = True          # set False to fall back to LLM translation
    llm_fallback_enabled: bool = True   # rule-based fallback when Gemini unavailable

    # ── Rate limits (per tenant, per minute) ─────────────────────────────────────
    widget_rate_limit: int = 60
    extension_rate_limit: int = 300

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_asyncpg_scheme(cls, v: str) -> str:
        """Render provides postgresql:// — asyncpg needs postgresql+asyncpg://"""
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
