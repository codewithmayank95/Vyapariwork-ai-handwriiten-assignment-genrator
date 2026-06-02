from __future__ import annotations

import os
import random
import uuid
from pathlib import Path
from typing import Iterable, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from config import FONTS_DIR, OUTPUTS_DIR, TEMP_DIR, TEMPLATES_DIR, ensure_folders


# =========================
# Configurable coordinates
# =========================
# These defaults match the placeholder templates included in this repo.
# If you replace templates with your real college sheets, adjust these values.

NAME_X = 190
NAME_Y = 110
ROLL_X = 190
ROLL_Y = 145
SUBJECT_X = 630
SUBJECT_Y = 145

START_X = 205
START_Y = 295
MAX_WIDTH = 930  # maximum text line width in pixels
MAX_Y = 1640  # last y position for text before page break

LINE_GAP = 45  # Increased for better readability with larger font
FONT_SIZE = 32  # Professional font size for handwritten look

PEN_COLOR = (20, 60, 160)  # blue ink


def _safe_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Try to load Kalam font (prefer Bold for better visibility); if missing, fall back to PIL default.
    """
    # Try Kalam-Bold first for better cursive appearance
    bold_font = FONTS_DIR / "Kalam-Bold.ttf"
    regular_font = FONTS_DIR / "Kalam-Regular.ttf"
    
    for font_path in [bold_font, regular_font]:
        try:
            if font_path.exists():
                return ImageFont.truetype(str(font_path), FONT_SIZE)
        except Exception:
            pass
    return ImageFont.load_default()


def _template_path(college: str) -> Path:
    key = (college or "").strip().lower()
    mapping = {
        "oist": TEMPLATES_DIR / "oist.png",
        "oct": TEMPLATES_DIR / "oct.png",
        "default": TEMPLATES_DIR / "default.png",
    }
    p = mapping.get(key, mapping["default"])
    if not p.exists():
        return mapping["default"]
    return p


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    text = (text or "").replace("\t", " ")
    text = " ".join(text.split())
    if not text:
        return []

    words = text.split(" ")
    lines: list[str] = []
    cur: list[str] = []

    for w in words:
        trial = (" ".join(cur + [w])).strip()
        if not cur:
            cur = [w]
            continue
        if _measure_text(draw, trial, font) <= max_width:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines
 for realistic handwritten appearance.
    Subtle jitter that doesn't affect readability.
    """
    jitter_x = random.randint(-1, 1)  # Reduced for better alignment
    jitter_y = random.randint(-1, 1)  # Reduced for better alignment
    jitter_gap = random.randint(-1, 1) if (line_idx % 4
    """
    jitter_x = random.randint(-2, 2)
    jitter_y = random.randint(-2, 2)
    jitter_gap = random.randint(-2, 2) if (line_idx % 3 == 0) else 0
    return x + jitter_x, y + jitter_y, jitter_gap


def _compose_page(
    template_img: Image.Image,
    *,
    name: str,
    roll_number: str,
    subject: str,
    header_written: bool,
) -> Image.Image:
    img = template_img.copy().convert("RGB")
    draw = ImageDraw.Draw(img)
    font = _safe_font()

    if header_written:
        draw.text((NAME_X, NAME_Y), name, fill=PEN_COLOR, font=font)
        draw.text((ROLL_X, ROLL_Y), roll_number, fill=PEN_COLOR, font=font)
        draw.text((SUBJECT_X, SUBJECT_Y), subject, fill=PEN_COLOR, font=font)

    return img


def render_handwritten_pdf(
    *,
    name: str,
    roll_number: str,
    subject: str,
    college: str,
    questions: List[str],
    answers: List[str],
) -> tuple[str, int]:
    """
    Renders handwritten-style pages and returns (pdf_relative_url, pages).
    Saves intermediate page images into backend/temp and final PDF into backend/outputs.
    """
    ensure_folders()

    template_path = _template_path(college)
    template_img = Image.open(str(template_path)).convert("RGB")

    job_id = uuid.uuid4().hex
    page_paths: list[Path] = []

    # Prepare lines to write
    pairs = list(zip(questions, answers))
    if not pairs:
        raise ValueError("No questions/answers to render.")

    font = _safe_font()

    def new_page(first_page: bool) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
        img = _compose_page(
            template_img,
            name=name,
            roll_number=roll_number,
            subject=subject,
            header_written=True,
        )
        d = ImageDraw.Draw(img)
        y = START_Y
        # On first page, write a tiny spacer so header feels separated
        if first_page:
            y += 0
        return img, d, y

    img, draw, y = new_page(first_page=True)
    page_index = 1

    def save_page(current_img: Image.Image) -> None:
        nonlocal page_index
        path = TEMP_DIR / f"{job_id}_page_{page_index:03d}.png"
        current_img.save(str(path), format="PNG")
        page_paths.append(path)
        page_index += 1

    # Helper to draw a single line and move y
    def write_line(line: str, line_idx: int) -> None:
        nonlocal y
        xj, yj, gap_j = _add_handwriting_jitter(START_X, y, line_idx)
        # Use baseline alignment for consistency
        draw.text((xj, yj), line, fill=PEN_COLOR, font=font, anchor="lt")
        y += LINE_GAP + gap_j

    line_idx = 0

    for qi, (q, a) in enumerate(pairs, start=1):
        # Question header
        q_header = f"Q{qi}) {q.strip()}"
        q_lines = _wrap_text(draw, q_header, font, MAX_WIDTH)
        for ln in q_lines:
            if y > MAX_Y:
                save_page(img)
                img, draw, y = new_page(first_page=False)
            write_line(ln, line_idx)
            line_idx += 1

        # Answer body
        # Keep paragraphs by splitting on blank lines, then wrapping each paragraph separately.
        paragraphs = [p.strip() for p in (a or "").splitlines()]
        cur_para: list[str] = []
        normalized_paras: list[str] = []
        for ln in paragraphs:
            if not ln.strip():
                if cur_para:
                    normalized_paras.append(" ".join(cur_para).strip())
                    cur_para = []
            else:
                cur_para.append(ln.strip())
        if cur_para:
            normalized_paras.append(" ".join(cur_para).strip())

        if not normalized_paras:
            normalized_paras = [a.strip()] if (a or "").strip() else []

        for pi, para in enumerate(normalized_paras):
            if not para:
                continue
            # small indent for answer
            wrapped = _wrap_text(draw, para, font, MAX_WIDTH)
            for ln in wrapped:
                if y > MAX_Y:
                    save_page(img)
                    img, draw, y = new_page(first_page=False)
                write_line(ln, line_idx)
                line_idx += 1
            # paragraph spacer
            y += int(LINE_GAP * 0.3)

        # Extra spacing between questions
        y += int(LINE_GAP * 0.6)  # Increased spacing for clarity

    # Save last page
    save_page(img)

    output_name = f"assignment_{job_id}.pdf"
    output_path = OUTPUTS_DIR / output_name

    # Merge pages into PDF
    try:
        import img2pdf  # type: ignore

        with open(output_path, "wb") as f:
            f.write(img2pdf.convert([str(p) for p in page_paths]))
    except Exception:
        # Fallback: Pillow multi-page PDF
        images = [Image.open(str(p)).convert("RGB") for p in page_paths]
        if not images:
            raise RuntimeError("No pages generated.")
        first, rest = images[0], images[1:]
        first.save(str(output_path), save_all=True, append_images=rest)
        for im in images:
            try:
                im.close()
            except Exception:
                pass

    # Cleanup temp PNGs
    for p in page_paths:
        try:
            os.remove(p)
        except Exception:
            pass

    pdf_url = f"/outputs/{output_name}"
    return pdf_url, len(page_paths)

