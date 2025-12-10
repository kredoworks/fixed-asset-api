from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from config.database import get_database_url

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "env" / ".env.staging"


class StageSettings(BaseSettings):
    APP_ENV: str = "stage"
    SECRET_KEY: str | None = None
    DEBUG: bool = False
    
    # Database components
    DB_DRIVER: str = "postgresql+asyncpg"
    DB_HOST: str | None = None
    DB_PORT: int = 5432
    DB_USER: str | None = None
    DB_PASSWORD: str | None = None
    DB_NAME: str | None = None

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
    )
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL from components"""
        return get_database_url(
            driver=self.DB_DRIVER,
            host=self.DB_HOST,
            port=self.DB_PORT,
            user=self.DB_USER,
            password=self.DB_PASSWORD,
            name=self.DB_NAME,
        )
