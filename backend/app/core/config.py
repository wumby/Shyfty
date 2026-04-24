from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_database_url() -> str:
    project_root_db = Path(__file__).resolve().parents[3] / "shyfty.db"
    if project_root_db.exists():
        return f"sqlite:///{project_root_db}"
    return "postgresql+psycopg://postgres:postgres@localhost:5432/shyfty"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Shyfty"
    database_url: str = _default_database_url()
    cors_origins: list[str] = [
        "http://127.0.0.1:5175",
        "http://localhost:5175",
    ]
    espn_timeout_seconds: float = 20.0
    espn_nfl_bootstrap_weeks: int = 6
    espn_nfl_incremental_weeks: int = 2


settings = Settings()
