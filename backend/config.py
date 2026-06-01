from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _try_load_dotenv() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        return
    load_dotenv()


_try_load_dotenv()


BASE_DIR = Path(__file__).resolve().parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
TEMP_DIR = BASE_DIR / "temp"
TEMPLATES_DIR = BASE_DIR / "templates"
FONTS_DIR = BASE_DIR / "fonts"


def ensure_folders() -> None:
    for p in (UPLOADS_DIR, OUTPUTS_DIR, TEMP_DIR, TEMPLATES_DIR, FONTS_DIR):
        p.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY") or None

    frontend_url: str | None = os.getenv("FRONTEND_URL") or None

    supabase_url: str | None = os.getenv("SUPABASE_URL") or None
    supabase_service_key: str | None = os.getenv("SUPABASE_SERVICE_KEY") or None

    firebase_credentials_path: str | None = os.getenv("FIREBASE_CREDENTIALS_PATH") or None


SETTINGS = Settings()

