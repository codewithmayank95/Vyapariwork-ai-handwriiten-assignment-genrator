from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _as_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def _csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


_load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
TEMP_DIR = BASE_DIR / "tmp"
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
TEMPLATES_DIR = BASE_DIR / "templates"
FONTS_DIR = BASE_DIR / "fonts"


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None
    use_image_generation: bool = _as_bool(os.getenv("USE_IMAGE_GENERATION"), True)
    gemini_image_model: str = os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    cors_origins: tuple[str, ...] = _csv(os.getenv("CORS_ORIGINS"))
    max_upload_mb: int = _as_int(os.getenv("MAX_UPLOAD_MB"), 20)
    page_char_limit: int = _as_int(os.getenv("PAGE_CHAR_LIMIT"), 1250)
    image_retry_count: int = _as_int(os.getenv("IMAGE_RETRY_COUNT"), 2)
    image_retry_delay_seconds: float = _as_float(os.getenv("IMAGE_RETRY_DELAY_SECONDS"), 2.0)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


SETTINGS = Settings()


def ensure_folders() -> None:
    for path in (TEMP_DIR, UPLOADS_DIR, OUTPUTS_DIR, TEMPLATES_DIR, FONTS_DIR):
        path.mkdir(parents=True, exist_ok=True)
