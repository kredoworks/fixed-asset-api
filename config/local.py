from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "env" / ".env.local"


class LocalSettings(BaseSettings):
    DATABASE_URL: str | None = None
    APP_ENV: str = "local"
    SECRET_KEY: str | None = None
    DEBUG: bool = True

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
    )
