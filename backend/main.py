from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from ai_answer import generate_answers
from auth import AuthError, verify_firebase_token
from config import OUTPUTS_DIR, UPLOADS_DIR, SETTINGS, ensure_folders
from database import create_job, get_job, is_supabase_configured, update_job
from extract_questions import extract_questions_from_pdf, parse_manual_questions
from generator import render_handwritten_pdf

ensure_folders()

app = FastAPI(title="AI Handwritten Assignment PDF Generator")

# Static PDFs
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")

# CORS
allow_origins = ["null"]
if SETTINGS.frontend_url:
    allow_origins.append(SETTINGS.frontend_url)

allow_origin_regex = r"^(https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?|https://.*\\.pages\\.dev)$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/job/{job_id}")
def job(job_id: str):
    if not is_supabase_configured():
        rec = get_job(job_id)
        if not rec:
            return {"success": False, "message": "Supabase not configured; no job found locally."}
        return {"success": True, "job": rec, "note": "Supabase not configured; returning local in-memory job."}
    rec = get_job(job_id)
    if not rec:
        return {"success": False, "message": "Job not found."}
    return {"success": True, "job": rec}


@app.post("/generate-pdf")
async def generate_pdf(
    name: str = Form(...),
    roll_number: str = Form(...),
    subject: str = Form(...),
    college: str = Form(...),
    answer_length: str = Form(...),
    questions: Optional[str] = Form(None),
    assignment_pdf: Optional[UploadFile] = File(None),
    firebase_token: Optional[str] = Form(None),
):
    user_id: str | None = None
    try:
        user_id = verify_firebase_token(firebase_token)
    except AuthError as e:
        return JSONResponse(status_code=401, content={"success": False, "message": str(e)})

    questions_list = []
    questions_text_for_db = ""

    if questions and questions.strip():
        questions_list = parse_manual_questions(questions)
        questions_text_for_db = questions.strip()
    elif assignment_pdf is not None:
        # Save upload
        if not assignment_pdf.filename or not assignment_pdf.filename.lower().endswith(".pdf"):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Please upload a valid PDF file."},
            )

        upload_id = uuid.uuid4().hex
        upload_path = UPLOADS_DIR / f"{upload_id}_{Path(assignment_pdf.filename).name}"
        try:
            data = await assignment_pdf.read()
            upload_path.write_bytes(data)
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Failed to save uploaded PDF: {e}"},
            )

        try:
            questions_list = extract_questions_from_pdf(upload_path)
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"Failed to extract questions from PDF: {e}"},
            )
        questions_text_for_db = "\n".join(questions_list)
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "Provide either manual questions or an assignment PDF."},
        )

    if not questions_list:
        return JSONResponse(
            status_code=400,
            content={"success": False, "message": "No questions found. Please enter questions or upload a clearer PDF."},
        )

    # Create job record (optional)
    job_id = create_job(
        user_id=user_id,
        name=name.strip(),
        roll_number=roll_number.strip(),
        subject=subject.strip(),
        college=college.strip().lower(),
        questions_text=questions_text_for_db,
    )
    update_job(job_id, status="processing")

    try:
        answers = generate_answers(questions_list, answer_length)
        pdf_url, pages = render_handwritten_pdf(
            name=name.strip(),
            roll_number=roll_number.strip(),
            subject=subject.strip(),
            college=college.strip().lower(),
            questions=questions_list,
            answers=answers,
        )
        update_job(job_id, status="done", pdf_url=pdf_url, pages=pages)
        return {
            "success": True,
            "job_id": job_id,
            "pdf_url": pdf_url,
            "pages": pages,
        }
    except Exception as e:
        update_job(job_id, status="error")
        return JSONResponse(status_code=500, content={"success": False, "message": f"Generation failed: {e}"})
