from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from config import SETTINGS


@dataclass
class JobRecord:
    id: str
    user_id: str | None
    name: str
    roll_number: str
    subject: str
    college: str
    questions: str
    status: str
    pdf_url: str | None = None
    pages: int | None = None
    created_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "roll_number": self.roll_number,
            "subject": self.subject,
            "college": self.college,
            "questions": self.questions,
            "status": self.status,
            "pdf_url": self.pdf_url,
            "pages": self.pages,
            "created_at": self.created_at,
        }


LOCAL_JOBS: Dict[str, JobRecord] = {}


def _get_supabase_client():
    if not (SETTINGS.supabase_url and SETTINGS.supabase_service_key):
        return None
    try:
        from supabase import create_client  # type: ignore
    except Exception:
        return None
    try:
        return create_client(SETTINGS.supabase_url, SETTINGS.supabase_service_key)
    except Exception:
        return None


def is_supabase_configured() -> bool:
    return _get_supabase_client() is not None


def create_job(
    *,
    user_id: str | None,
    name: str,
    roll_number: str,
    subject: str,
    college: str,
    questions_text: str,
) -> str:
    job_id = str(uuid.uuid4())
    record = JobRecord(
        id=job_id,
        user_id=user_id,
        name=name,
        roll_number=roll_number,
        subject=subject,
        college=college,
        questions=questions_text,
        status="created",
        created_at=time.time(),
    )

    sb = _get_supabase_client()
    if sb is None:
        LOCAL_JOBS[job_id] = record
        return job_id

    # Supabase insert (optional)
    try:
        sb.table("pdf_jobs").insert(
            {
                "id": record.id,
                "user_id": record.user_id,
                "name": record.name,
                "roll_number": record.roll_number,
                "subject": record.subject,
                "college": record.college,
                "questions": record.questions,
                "status": record.status,
            }
        ).execute()
    except Exception:
        # Don't fail the request if DB is down; fall back to local memory.
        LOCAL_JOBS[job_id] = record
    return job_id


def update_job(
    job_id: str,
    *,
    status: str,
    pdf_url: str | None = None,
    pages: int | None = None,
) -> None:
    sb = _get_supabase_client()
    if sb is None:
        rec = LOCAL_JOBS.get(job_id)
        if not rec:
            return
        rec.status = status
        if pdf_url is not None:
            rec.pdf_url = pdf_url
        if pages is not None:
            rec.pages = pages
        return

    try:
        data: Dict[str, Any] = {"status": status}
        if pdf_url is not None:
            data["pdf_url"] = pdf_url
        if pages is not None:
            data["pages"] = pages
        sb.table("pdf_jobs").update(data).eq("id", job_id).execute()
    except Exception:
        # Best-effort only
        return


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    sb = _get_supabase_client()
    if sb is None:
        rec = LOCAL_JOBS.get(job_id)
        return rec.to_dict() if rec else None

    try:
        res = sb.table("pdf_jobs").select("*").eq("id", job_id).limit(1).execute()
        data = getattr(res, "data", None) or []
        return data[0] if data else None
    except Exception:
        # fall back to local if present
        rec = LOCAL_JOBS.get(job_id)
        return rec.to_dict() if rec else None

