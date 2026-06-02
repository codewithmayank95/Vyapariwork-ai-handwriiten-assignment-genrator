from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..config import SETTINGS
from ..services.fallback_renderer import render_handwriting_page
from ..services.gemini_image import GeminiImageError, GeminiImageService
from ..services.page_splitter import split_text_into_pages
from ..services.pdf_builder import build_pdf_from_images
from ..services.text_extractor import TextExtractionError, clean_text, extract_text_from_upload
from ..utils.file_utils import cleanup_path, create_job_dir, make_job_id


router = APIRouter()

_PROGRESS: dict[str, dict[str, Any]] = {}
_PROGRESS_LOCK = threading.Lock()


@router.get("/api/progress/{job_id}")
def get_progress(job_id: str) -> dict[str, Any]:
    with _PROGRESS_LOCK:
        progress = _PROGRESS.get(job_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found.")
    return progress


@router.post("/api/generate")
async def generate_assignment(
    text: str | None = Form(None),
    mode: str = Form("standard"),
    job_id: str | None = Form(None),
    pdf: UploadFile | None = File(None),
    assignment_pdf: UploadFile | None = File(None),
) -> FileResponse:
    progress_id = make_job_id(job_id)
    upload = pdf or assignment_pdf
    selected_mode = _normalize_mode(mode)

    has_text = bool(text and text.strip())
    has_pdf = bool(upload and upload.filename)
    if has_text and has_pdf:
        raise HTTPException(status_code=400, detail="Use either pasted text or one PDF, not both.")
    if not has_text and not has_pdf:
        raise HTTPException(status_code=400, detail="Paste assignment text or upload a PDF.")

    job_dir: Path | None = None
    gemini: GeminiImageService | None = None
    used_fallback = selected_mode == "standard"

    try:
        _set_progress(progress_id, status="extracting", page=0, total_pages=0, percent=5, message="Preparing input...")

        if has_text:
            source_text = clean_text(text)
        elif upload is not None:
            source_text = await extract_text_from_upload(upload, SETTINGS.max_upload_bytes)
        else:
            source_text = ""

        if not source_text:
            raise HTTPException(status_code=400, detail="No assignment text was found.")

        _set_progress(progress_id, status="splitting", percent=12, message="Splitting pages...")
        chunks = split_text_into_pages(source_text, SETTINGS.page_char_limit)
        if not chunks:
            raise HTTPException(status_code=400, detail="Text is too short to generate a page.")

        total_pages = len(chunks)
        job_dir = create_job_dir(progress_id)
        image_paths: list[Path] = []

        if selected_mode == "ultra" and SETTINGS.use_image_generation:
            try:
                gemini = GeminiImageService(SETTINGS)
            except GeminiImageError:
                used_fallback = True
        else:
            used_fallback = True

        for page_index, chunk in enumerate(chunks, start=1):
            page_path = job_dir / f"page_{page_index:03d}.png"
            progress_base = 15 + int((page_index - 1) / total_pages * 75)

            if gemini is not None:
                _set_progress(
                    progress_id,
                    status="generating",
                    page=page_index,
                    total_pages=total_pages,
                    percent=progress_base,
                    message=f"Page {page_index}/{total_pages} generating...",
                )
                try:
                    await asyncio.to_thread(gemini.generate_page_image, chunk, page_index, total_pages, page_path)
                except GeminiImageError:
                    used_fallback = True
                    _set_progress(
                        progress_id,
                        status="fallback",
                        page=page_index,
                        total_pages=total_pages,
                        percent=progress_base,
                        message=f"Page {page_index}/{total_pages} using fallback renderer...",
                    )
                    await asyncio.to_thread(render_handwriting_page, chunk, page_path, page_index, total_pages)
            else:
                _set_progress(
                    progress_id,
                    status="fallback",
                    page=page_index,
                    total_pages=total_pages,
                    percent=progress_base,
                    message=f"Page {page_index}/{total_pages} rendering...",
                )
                await asyncio.to_thread(render_handwriting_page, chunk, page_path, page_index, total_pages)

            image_paths.append(page_path)
            _set_progress(
                progress_id,
                page=page_index,
                total_pages=total_pages,
                percent=15 + int(page_index / total_pages * 75),
                message=f"Page {page_index}/{total_pages} complete.",
            )

        _set_progress(progress_id, status="building", percent=94, message="Combining PDF...")
        output_path = await asyncio.to_thread(build_pdf_from_images, image_paths, job_dir / "assignment.pdf")

        _set_progress(
            progress_id,
            status="done",
            page=total_pages,
            total_pages=total_pages,
            percent=100,
            message="PDF ready.",
        )

        headers = {
            "X-Job-Id": progress_id,
            "X-Total-Pages": str(total_pages),
            "X-Generation-Mode": selected_mode,
            "X-Fallback-Used": str(used_fallback).lower(),
        }
        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=f"handwritten-assignment-{progress_id[:8]}.pdf",
            headers=headers,
            background=BackgroundTask(cleanup_path, job_dir),
        )
    except HTTPException:
        if job_dir is not None:
            cleanup_path(job_dir)
        raise
    except TextExtractionError as exc:
        if job_dir is not None:
            cleanup_path(job_dir)
        _set_progress(progress_id, status="error", percent=0, message=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        if job_dir is not None:
            cleanup_path(job_dir)
        _set_progress(progress_id, status="error", percent=0, message="Generation failed.")
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc
    finally:
        if gemini is not None:
            gemini.close()


def _normalize_mode(mode: str) -> str:
    value = (mode or "standard").strip().lower()
    aliases = {
        "standard": "standard",
        "standard_pdf": "standard",
        "standard-pdf": "standard",
        "ultra": "ultra",
        "ultra_real": "ultra",
        "ultra-real": "ultra",
        "image": "ultra",
    }
    if value not in aliases:
        raise HTTPException(status_code=400, detail="Mode must be standard or ultra.")
    return aliases[value]


def _set_progress(job_id: str, **updates: Any) -> None:
    payload = {
        "job_id": job_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **updates,
    }
    with _PROGRESS_LOCK:
        current = _PROGRESS.get(job_id, {})
        current.update(payload)
        _PROGRESS[job_id] = current
