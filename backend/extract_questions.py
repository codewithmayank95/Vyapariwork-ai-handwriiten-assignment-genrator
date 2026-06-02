from __future__ import annotations

import re
from pathlib import Path
from typing import List


QUESTION_START_RE = re.compile(
    r"^\\s*(?:"
    r"(?:Q\\s*\\.?\\s*\\d+)\\s*[:\\).\\-]*\\s*"
    r"|(?:Question\\s*\\d+)\\s*[:\\).\\-]*\\s*"
    r"|(?:\\d+)\\s*[\\).:-]\\s*"
    r")",
    re.IGNORECASE,
)

LEADING_MARKER_RE = re.compile(
    r"^\\s*(?:"
    r"(?:Q\\s*\\.?\\s*\\d+)\\s*[:\\).\\-]*\\s*"
    r"|(?:Question\\s*\\d+)\\s*[:\\).\\-]*\\s*"
    r"|(?:\\d+)\\s*[\\).:-]\\s*"
    r")",
    re.IGNORECASE,
)


def parse_questions_from_text(text: str) -> List[str]:
    if not text or not text.strip():
        return []

    # Normalize whitespace and lines
    lines = [ln.strip() for ln in text.replace("\r", "\n").split("\n")]

    questions: list[str] = []
    buf: list[str] = []

    def flush():
        nonlocal buf
        if not buf:
            return
        q = " ".join([b for b in buf if b]).strip()
        q = re.sub(r"\\s+", " ", q)
        q = LEADING_MARKER_RE.sub("", q).strip()
        if q and len(q) >= 6:
            questions.append(q)
        buf = []

    for ln in lines:
        if not ln:
            continue
        if QUESTION_START_RE.match(ln) and buf:
            flush()
        buf.append(ln)

    flush()

    # If we didn't detect any markers, fall back to treating each non-empty line as a question.
    if not questions:
        raw = [re.sub(r"\\s+", " ", ln).strip() for ln in lines if ln.strip()]
        questions = [q for q in raw if len(q) >= 6]

    # Deduplicate (preserve order)
    seen = set()
    out: list[str] = []
    for q in questions:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(q)
    return out


def parse_manual_questions(questions_text: str) -> List[str]:
    return parse_questions_from_text(questions_text or "")


def _extract_text_pdfplumber(pdf_path: Path) -> str:
    import pdfplumber  # type: ignore

    texts: list[str] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                texts.append(t)
    return "\n".join(texts)


def _extract_text_pymupdf(pdf_path: Path) -> str:
    import fitz  # type: ignore

    doc = fitz.open(str(pdf_path))
    texts: list[str] = []
    try:
        for page in doc:
            try:
                t = page.get_text("text") or ""
            except Exception:
                t = ""
            if t.strip():
                texts.append(t)
    finally:
        doc.close()
    return "\n".join(texts)


def extract_questions_from_pdf(pdf_path: str | Path) -> List[str]:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    text = ""
    # 1) Try pdfplumber text extraction
    try:
        text = _extract_text_pdfplumber(path)
    except Exception:
        text = ""

    # 2) Fallback to PyMuPDF if needed
    if not text.strip():
        try:
            text = _extract_text_pymupdf(path)
        except Exception:
            text = ""

    questions = parse_questions_from_text(text)
    return questions

