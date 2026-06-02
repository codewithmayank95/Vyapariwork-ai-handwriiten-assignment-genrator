from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from backend.config import SETTINGS
from backend.services.fallback_renderer import render_handwriting_page
from backend.services.gemini_image import GeminiImageError, GeminiImageService
from backend.services.page_splitter import split_text_into_pages
from backend.services.pdf_builder import build_pdf_from_images
from backend.services.text_extractor import TextExtractionError, clean_text, extract_text_from_upload
from backend.utils.file_utils import cleanup_path, create_job_dir, make_job_id


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


@router.options("/api/generate")
@router.options("/generate-pdf")
def generation_options() -> Response:
    return Response(status_code=204)


@router.post("/generate-pdf")
@router.post("/api/generate")
async def generate_assignment(
    text: str | None = Form(None),
    mode: str = Form("standard"),
    job_id: str | None = Form(None),
    student_name: str | None = Form(None),
    name: str | None = Form(None),
    roll_number: str | None = Form(None),
    college: str = Form("oist"),
    pdf: UploadFile | None = File(None),
    assignment_pdf: UploadFile | None = File(None),
    template_image: UploadFile | None = File(None),
) -> FileResponse:
    progress_id = make_job_id(job_id)
    upload = pdf or assignment_pdf
    selected_mode = _normalize_mode(mode)
    display_name = clean_text(student_name or name or "")
    display_roll = clean_text(roll_number or "")
    college_key = _normalize_college(college)

    if not display_name:
        raise HTTPException(status_code=400, detail="Student name is required.")
    if not display_roll:
        raise HTTPException(status_code=400, detail="Roll number is required.")
    if college_key == "other" and not (template_image and template_image.filename):
        raise HTTPException(status_code=400, detail="Upload your college blank sessional page for Other college.")

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
        template_path = await _resolve_template_path(college_key, template_image, job_dir)
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
                    await asyncio.to_thread(
                        gemini.generate_page_image,
                        chunk,
                        page_index,
                        total_pages,
                        page_path,
                        display_name,
                        display_roll,
                        college_key,
                    )
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
                    await asyncio.to_thread(
                        render_handwriting_page,
                        chunk,
                        page_path,
                        page_index,
                        total_pages,
                        display_name,
                        display_roll,
                        college_key,
                        template_path,
                    )
            else:
                _set_progress(
                    progress_id,
                    status="fallback",
                    page=page_index,
                    total_pages=total_pages,
                    percent=progress_base,
                    message=f"Page {page_index}/{total_pages} rendering...",
                )
                await asyncio.to_thread(
                    render_handwriting_page,
                    chunk,
                    page_path,
                    page_index,
                    total_pages,
                    display_name,
                    display_roll,
                    college_key,
                    template_path,
                )

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


def _normalize_college(college: str) -> str:
    value = (college or "oist").strip().lower()
    aliases = {
        "oist": "oist",
        "oct": "oct",
        "other": "other",
        "default": "default",
    }
    if value not in aliases:
        raise HTTPException(status_code=400, detail="College must be OIST, OCT, or Other.")
    return aliases[value]


async def _resolve_template_path(college: str, template_image: UploadFile | None, job_dir: Path) -> Path | None:
    if college in {"oist", "oct", "default"}:
        template_path = Path(__file__).resolve().parents[1] / "templates" / f"{college}.png"
        if template_path.exists():
            return template_path
        return None

    if template_image is None:
        return None

    content_type = (template_image.content_type or "").lower()
    filename = template_image.filename or ""
    allowed_suffixes = {".png", ".jpg", ".jpeg"}
    if Path(filename).suffix.lower() not in allowed_suffixes and not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Blank sessional page must be a PNG or JPG image.")

    data = await template_image.read()
    if not data:
        raise HTTPException(status_code=400, detail="Blank sessional page image is empty.")
    if len(data) > SETTINGS.max_upload_bytes:
        raise HTTPException(status_code=400, detail="Blank sessional page image is too large.")

    output_path = job_dir / "custom_template.png"
    output_path.write_bytes(data)
    try:
        from PIL import Image

        with Image.open(output_path) as image:
            image.verify()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Uploaded blank sessional page is not a valid image.") from exc

    return output_path


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
