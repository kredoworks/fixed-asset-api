from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

# BaseSettings is provided by the `pydantic-settings` package in Pydantic v2

# Project root (one level up from this config package)
ROOT = Path(__file__).resolve().parents[1]

# Mode selector: use MODE env var if set, else fall back to APP_ENV, then 'local'
MODE = os.environ.get("MODE") or os.environ.get("APP_ENV") or "local"
MODE = MODE.lower()


def _env_file_for(mode: str) -> Optional[str]:
    candidate = ROOT / "env" / f".env.{mode}"
    if candidate.exists():
        return str(candidate)
    fallback = ROOT / "env" / ".env.local"
    if fallback.exists():
        return str(fallback)
    return None


# Import per-environment settings classes
from .local import LocalSettings
from .stage import StageSettings
from .prod import ProdSettings
from .dev import DevSettings
from .test import TestSettings


_MAPPING = {
    "local": LocalSettings,
    "stage": StageSettings,
    "staging": StageSettings,
    "prod": ProdSettings,
    "production": ProdSettings,
    "dev": DevSettings,
    "test": TestSettings,
}


def _choose_settings_class(mode: str):
    return _MAPPING.get(mode, LocalSettings)


# Instantiate settings from selected class. Pydantic BaseSettings will read the file
# specified in the inner class `Config.env_file` of each module.
SettingsClass = _choose_settings_class(MODE)
settings = SettingsClass()

__all__ = ["settings", "SettingsClass", "MODE"]
