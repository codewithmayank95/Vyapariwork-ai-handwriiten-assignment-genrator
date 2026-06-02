from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

from ..config import TEMP_DIR


_SAFE_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_-]+")


def make_job_id(candidate: str | None = None) -> str:
    if candidate:
        cleaned = _SAFE_ID_PATTERN.sub("-", candidate.strip())[:80].strip("-")
        if cleaned:
            return cleaned
    return uuid.uuid4().hex


def create_job_dir(job_id: str) -> Path:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    path = TEMP_DIR / job_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_path(path: str | Path) -> None:
    target = Path(path).resolve()
    temp_root = TEMP_DIR.resolve()
    if target != temp_root and temp_root in target.parents:
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink(missing_ok=True)
