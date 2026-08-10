from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv


load_dotenv()


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


@dataclass(frozen=True)
class Settings:
    base_url: str = os.getenv("FLRU_BASE_URL", "https://www.fl.ru").rstrip("/")
    login: str | None = os.getenv("FLRU_LOGIN") or None
    password: str | None = os.getenv("FLRU_PASSWORD") or None
    browser_profile: Path = Path(os.getenv("FLRU_BROWSER_PROFILE", "./data/browser-profile"))
    storage_state: Path = Path(os.getenv("FLRU_STORAGE_STATE", "./data/storage_state.json"))
    database_path: Path = Path(os.getenv("FLRU_DATABASE", "./data/flru_mcp.sqlite3"))
    expertise_profile: Path = Path(os.getenv("FLRU_EXPERTISE_PROFILE", "./config/expertise.yml"))
    headless: bool = _bool("FLRU_HEADLESS", False)
    debug: bool = _bool("FLRU_DEBUG", False)
    dry_run: bool = _bool("FLRU_DRY_RUN", True)
    delay_min_ms: int = _int("FLRU_REQUEST_DELAY_MIN_MS", 800)
    delay_max_ms: int = _int("FLRU_REQUEST_DELAY_MAX_MS", 1800)
    http_timeout: int = _int("FLRU_HTTP_TIMEOUT", 30)

    @property
    def debug_dir(self) -> Path:
        return Path("./data/debug")


def load_settings() -> Settings:
    settings = Settings()
    settings.browser_profile.mkdir(parents=True, exist_ok=True)
    settings.storage_state.parent.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    if settings.debug:
        settings.debug_dir.mkdir(parents=True, exist_ok=True)
    return settings


@dataclass(frozen=True)
class ExpertiseProfile:
    specializations: list[str]
    preferred_projects: list[str]
    excluded_projects: list[str]


def load_expertise_profile(path: Path) -> ExpertiseProfile:
    if not path.exists():
        return ExpertiseProfile([], [], [])
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ExpertiseProfile(
        specializations=list(data.get("specializations") or []),
        preferred_projects=list(data.get("preferred_projects") or []),
        excluded_projects=list(data.get("excluded_projects") or []),
    )

