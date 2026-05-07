from pathlib import Path
from urllib.parse import urlparse
from typing import Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    project_root_db = Path(__file__).resolve().parents[3] / "shyfty.db"
    if project_root_db.exists():
        return f"sqlite:///{project_root_db}"
    return "postgresql+psycopg://postgres:postgres@localhost:5432/shyfty"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Shyfty"
    app_env: str = "development"
    database_url: str = _default_database_url()
    port: int = 8001
    frontend_origin: Optional[str] = None
    api_public_url: Optional[str] = None
    trust_proxy_headers: bool = False
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    admin_emails: list[str] = []
    cors_origins: list[str] = [
        "http://127.0.0.1:5175",
        "http://localhost:5175",
    ]
    espn_timeout_seconds: float = 20.0
    espn_nfl_bootstrap_weeks: int = 6
    espn_nfl_incremental_weeks: int = 2
    sync_poll_interval_minutes: int = 30
    sync_scheduler_enabled: bool = True
    sync_run_on_startup: bool = False
    sync_lookback_days: int = 1
    sync_lookahead_days: int = 1
    stat_correction_lookback_hours: int = 48
    enable_nba_sync: bool = True
    enable_nfl_sync: bool = False
    session_secret: str = "dev-session-secret-change-me"
    jwt_secret: str = "dev-jwt-secret-change-me"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_cookie_max_age_seconds: int = 60 * 60 * 24 * 30
    auth_rate_limit_window_seconds: int = 300
    auth_rate_limit_max_attempts: int = 10
    csrf_cookie_name: str = "shyfty_csrf"
    csrf_header_name: str = "X-CSRF-Token"
    csrf_cookie_secure: bool = False
    csrf_cookie_samesite: str = "lax"
    csrf_cookie_max_age_seconds: int = 60 * 60 * 24 * 30

    # Email / SMTP — leave blank to skip sending (reset link logs to console instead)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_address: str = ""
    smtp_from_name: str = "Shyfty"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def _parse_allowed_hosts(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("admin_emails", mode="before")
    @classmethod
    def _parse_admin_emails(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [item.strip().lower() for item in value.split(",") if item.strip()]
        return [str(item).strip().lower() for item in value if str(item).strip()]

    @field_validator("auth_cookie_samesite", "csrf_cookie_samesite")
    @classmethod
    def _normalize_samesite(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError("cookie SameSite must be one of: lax, strict, none")
        return normalized

    @model_validator(mode="after")
    def _validate_production(self):
        if self.is_production:
            if self.database_url.startswith("sqlite"):
                raise ValueError("SQLite is not allowed in production. Use a PostgreSQL DATABASE_URL.")
            if self.session_secret.strip() in {"", "dev-session-secret-change-me"}:
                raise ValueError("SESSION_SECRET must be set to a non-default value in production.")
            if self.jwt_secret.strip() in {"", "dev-jwt-secret-change-me"}:
                raise ValueError("JWT_SECRET must be set to a non-default value in production.")
            if not (self.frontend_origin or "").strip():
                raise ValueError("FRONTEND_ORIGIN is required in production.")
            if not (self.api_public_url or "").strip():
                raise ValueError("API_PUBLIC_URL is required in production.")
            if not self.allowed_hosts:
                raise ValueError("ALLOWED_HOSTS is required in production.")
            if not self.admin_emails:
                raise ValueError("ADMIN_EMAILS is required in production.")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @property
    def sync_scheduler_enabled_effective(self) -> bool:
        if self.is_production:
            return self.sync_scheduler_enabled
        return True

    @property
    def auth_cookie_secure_effective(self) -> bool:
        return self.auth_cookie_secure or self.is_production

    @property
    def auth_cookie_samesite_effective(self) -> str:
        if self.cross_site_frontend_backend and self.auth_cookie_samesite == "lax":
            return "none"
        return self.auth_cookie_samesite

    @property
    def csrf_cookie_secure_effective(self) -> bool:
        return self.csrf_cookie_secure or self.is_production

    @property
    def csrf_cookie_samesite_effective(self) -> str:
        if self.cross_site_frontend_backend and self.csrf_cookie_samesite == "lax":
            return "none"
        return self.csrf_cookie_samesite

    @property
    def cors_origins_effective(self) -> list[str]:
        if self.cors_origins:
            return self.cors_origins
        if self.frontend_origin:
            return [self.frontend_origin]
        return []

    @property
    def allowed_hosts_effective(self) -> list[str]:
        if self.allowed_hosts:
            return self.allowed_hosts
        return ["localhost", "127.0.0.1"]

    @property
    def trust_proxy_headers_effective(self) -> bool:
        return self.trust_proxy_headers or self.is_production

    @property
    def cross_site_frontend_backend(self) -> bool:
        if not self.is_production:
            return False
        if not self.frontend_origin or not self.api_public_url:
            return False
        frontend = urlparse(self.frontend_origin).netloc.lower()
        api = urlparse(self.api_public_url).netloc.lower()
        if not frontend or not api:
            return False
        return frontend != api

    @property
    def database_type(self) -> str:
        url = self.database_url.lower()
        if url.startswith("postgresql"):
            return "postgresql"
        if url.startswith("sqlite"):
            return "sqlite"
        return "other"


settings = Settings()
