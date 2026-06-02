from __future__ import annotations

import math
import os
import random
import uuid
from pathlib import Path
from typing import Iterable, List, Tuple

from PIL import Image, ImageDraw, ImageFont

from backend.config import FONTS_DIR, OUTPUTS_DIR, TEMP_DIR, TEMPLATES_DIR, ensure_folders


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

LINE_GAP = 45  # Spacing between notebook lines (optimized for 32px font on standard ruled paper)
FONT_SIZE = 32  # Base font size for body text (fills notebook lines naturally)
HEADING_FONT_SIZE = 36  # Larger size for question headings (makes them stand out)

PEN_COLOR = (31, 63, 163)  # Realistic blue ink (#1f3fa3)


def _safe_font(size: int = FONT_SIZE, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    Try to load Kalam font (prefer Bold for better visibility); if missing, fall back to PIL default.
    """
    # Try Kalam-Bold first for better cursive appearance
    bold_font = FONTS_DIR / "Kalam-Bold.ttf"
    regular_font = FONTS_DIR / "Kalam-Regular.ttf"
    
    # If bold is requested, try bold font first
    font_candidates = [bold_font, regular_font] if bold else [regular_font, bold_font]
    
    for font_path in font_candidates:
        try:
            if font_path.exists():
                return ImageFont.truetype(str(font_path), size)
        except Exception:
            pass
    return ImageFont.load_default()


def _create_char_image(char: str, font: ImageFont.FreeTypeFont, size_variation: float = 1.0) -> Image.Image:
    """
    Creates a small image with a single character for independent rendering.
    size_variation: 0.98-1.02 for slight size changes
    
    Features:
    - Transparent background for proper compositing
    - Slight color variation for realistic ink appearance
    - Proper padding and sizing for rotation support
    """
    # Create a temporary image to measure text
    temp_img = Image.new("RGBA", (150, 150), (255, 255, 255, 0))
    temp_draw = ImageDraw.Draw(temp_img)
    
    try:
        # Measure the character
        bbox = temp_draw.textbbox((10, 10), char, font=font)
        char_width = bbox[2] - bbox[0] + 8
        char_height = bbox[3] - bbox[1] + 8
    except:
        # Fallback dimensions
        char_width = 50
        char_height = 60
    
    # Create image for character with padding for rotation
    padding = 4
    char_img = Image.new("RGBA", (int(char_width * 1.2) + padding, int(char_height * 1.2) + padding), (255, 255, 255, 0))
    char_draw = ImageDraw.Draw(char_img)
    
    # Draw character with slight color variation for realism (mimics pen ink variation)
    color_var = random.randint(-4, 4)
    color_tuple = tuple(max(0, min(255, c + color_var)) for c in PEN_COLOR)
    color = color_tuple + (255,)  # Add alpha channel
    
    try:
        char_draw.text((padding, padding), char, font=font, fill=color)
    except Exception as e:
        # If drawing fails, return empty image
        pass
    
    return char_img


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


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
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


def _add_handwriting_jitter(x: int, y: int, line_idx: int, char_idx: int = 0) -> tuple[int, int, float]:
    """
    Adds subtle random jitter to coordinates for realistic handwritten appearance.
    Returns: (x, y, rotation_angle_in_degrees)
    """
    # Baseline jitter (vertical wobble)
    jitter_y = random.randint(-3, 3)
    
    # Horizontal jitter (slight character displacement)
    jitter_x = random.randint(-1, 2)
    
    # Character-level rotation (-1 to +1 degrees)
    rotation = random.uniform(-1.0, 1.0)
    
    # Add slight line-level jitter every few lines
    if line_idx % 5 == 0:
        jitter_x += random.randint(-1, 1)
    
    return x + jitter_x, y + jitter_y, rotation


def _draw_text_realistic(
    draw: ImageDraw.ImageDraw,
    img: Image.Image,
    text: str,
    x: int,
    y: int,
    font: ImageFont.FreeTypeFont,
    line_idx: int,
) -> int:
    """
    Draws text with per-character randomness for realistic handwritten appearance.
    Returns: x position after text (for layout calculations)
    
    Features:
    - Character-level size variation (±1-2%)
    - Slight rotation (-1° to +1°)
    - Baseline jitter (±3 pixels)
    - Horizontal displacement
    - Slight color variation
    - Proper spacing and alignment on notebook lines
    """
    current_x = x
    
    # Pre-calculate average character width for better spacing
    try:
        avg_char_width = font.getbbox("a")[2] - font.getbbox("a")[0]
    except:
        avg_char_width = 15  # Fallback value
    
    for char_idx, char in enumerate(text):
        if char == " ":
            # Space: typically narrower than regular characters
            current_x += int(avg_char_width * 0.35)
            continue
        
        # Get position with jitter
        char_x, char_y, rotation_angle = _add_handwriting_jitter(current_x, y, line_idx, char_idx)
        
        # Size variation for character (0.98 to 1.02)
        size_var = random.uniform(0.98, 1.02)
        
        try:
            # Create character image with realistic handwriting
            char_img = _create_char_image(char, font, size_var)
            
            # Apply rotation for slight slant if needed (small angles preserve readability)
            if abs(rotation_angle) > 0.05:  # Only rotate if angle is significant
                # For small rotations, expand=False keeps image size consistent
                char_img = char_img.rotate(rotation_angle, expand=False, resample=Image.BICUBIC)
            
            # Paste character onto main image with proper blending
            if char_img.mode == "RGBA":
                img.paste(char_img, (int(char_x), int(char_y)), char_img)
            else:
                img.paste(char_img, (int(char_x), int(char_y)))
        
        except Exception as e:
            # Fallback: use direct text rendering if character image fails
            try:
                color_var = random.randint(-3, 3)
                color = tuple(max(0, min(255, c + color_var)) for c in PEN_COLOR)
                draw.text((int(char_x), int(char_y)), char, font=font, fill=color)
            except:
                pass  # Skip if all else fails
        
        # Update x position for next character (accounting for size variation)
        char_width = avg_char_width
        try:
            char_width = font.getbbox(char)[2] - font.getbbox(char)[0]
        except:
            pass
        current_x += int(char_width * size_var * 0.93)  # Slight overlap for natural handwriting
    
    return current_x


def _compose_page(
    template_img: Image.Image,
    *,
    name: str,
    roll_number: str,
    subject: str,
    header_written: bool,
) -> Image.Image:
    """Compose a page with header information using realistic handwriting."""
    img = template_img.copy().convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = _safe_font(FONT_SIZE)

    if header_written:
        # Draw header information with handwriting effect
        # Name
        if name:
            _draw_text_realistic(draw, img, name, NAME_X, NAME_Y, font, line_idx=0)
        
        # Roll number
        if roll_number:
            _draw_text_realistic(draw, img, roll_number, ROLL_X, ROLL_Y, font, line_idx=1)
        
        # Subject
        if subject:
            _draw_text_realistic(draw, img, subject, SUBJECT_X, SUBJECT_Y, font, line_idx=2)

    # Convert back to RGB for compatibility
    return img.convert("RGB")


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
    Renders handwritten-style pages with realistic per-character randomness.
    
    This function creates a PDF that mimics authentic student handwriting with:
    - Per-character rotation and size variation
    - Baseline jitter for natural writing appearance
    - Realistic blue ink color (#1f3fa3)
    - Proper alignment on notebook ruled lines
    - Bold, larger question headings
    - Text wrapping according to page width
    - Multiple pages with consistent styling
    
    Returns: tuple of (pdf_relative_url, number_of_pages)
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

    font = _safe_font(FONT_SIZE)
    heading_font = _safe_font(HEADING_FONT_SIZE, bold=True)

    def new_page(first_page: bool) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
        """Create a new page from the template with header information."""
        img = _compose_page(
            template_img,
            name=name,
            roll_number=roll_number,
            subject=subject,
            header_written=True,
        )
        d = ImageDraw.Draw(img)
        y = START_Y
        return img, d, y

    img, draw, y = new_page(first_page=True)
    page_index = 1

    def save_page(current_img: Image.Image) -> None:
        """Save current page as PNG and add to page list."""
        nonlocal page_index
        path = TEMP_DIR / f"{job_id}_page_{page_index:03d}.png"
        current_img.save(str(path), format="PNG")
        page_paths.append(path)
        page_index += 1

    # Helper to draw a single line with realistic handwriting and move y
    def write_line(line: str, line_idx: int, is_heading: bool = False) -> None:
        """Draw a line with per-character handwriting effects."""
        nonlocal y
        current_font = heading_font if is_heading else font
        _draw_text_realistic(draw, img, line, START_X, y, current_font, line_idx)
        y += LINE_GAP

    line_idx = 0

    for qi, (q, a) in enumerate(pairs, start=1):
        # Question header - bold and larger for emphasis
        q_header = f"Q{qi}) {q.strip()}"
        q_lines = _wrap_text(draw, q_header, heading_font, MAX_WIDTH)
        
        for ln in q_lines:
            if y > MAX_Y:
                save_page(img)
                img, draw, y = new_page(first_page=False)
            write_line(ln, line_idx, is_heading=True)
            line_idx += 1

        # Answer body with natural paragraph breaks
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
            wrapped = _wrap_text(draw, para, font, MAX_WIDTH)
            for ln in wrapped:
                if y > MAX_Y:
                    save_page(img)
                    img, draw, y = new_page(first_page=False)
                write_line(ln, line_idx, is_heading=False)
                line_idx += 1
            # Paragraph spacer
            y += int(LINE_GAP * 0.3)

        # Extra spacing between questions
        y += int(LINE_GAP * 0.6)

    # Save last page
    save_page(img)

    output_name = f"assignment_{job_id}.pdf"
    output_path = OUTPUTS_DIR / output_name

    # Convert PNG pages to PDF using Pillow
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
