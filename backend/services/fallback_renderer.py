from __future__ import annotations

import random
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..config import FONTS_DIR


PAGE_WIDTH = 1240
PAGE_HEIGHT = 1754
MARGIN_LEFT = 138
MARGIN_RIGHT = 86
TOP_START = 178
LINE_HEIGHT = 42
BOTTOM_LIMIT = PAGE_HEIGHT - 112
INK = (28, 74, 154)
RULE = (176, 207, 238)
MARGIN_RULE = (222, 108, 102)
PAPER = (253, 253, 247)


def render_handwriting_page(page_text: str, output_path: Path, page_number: int, total_pages: int) -> Path:
    image = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)
    body_font = _load_font(32)
    header_font = _load_font(36)
    small_font = _load_font(22)

    _draw_paper(draw)
    _draw_header(draw, header_font, small_font, page_number, total_pages)
    _draw_body(draw, page_text, body_font, page_number)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)
    return output_path


def _load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        FONTS_DIR / "Kalam-Regular.ttf",
        FONTS_DIR / "Kalam-Bold.ttf",
        Path("C:/Windows/Fonts/segoepr.ttf"),
        Path("C:/Windows/Fonts/comic.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        try:
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_paper(draw: ImageDraw.ImageDraw) -> None:
    draw.rectangle((0, 0, PAGE_WIDTH - 1, PAGE_HEIGHT - 1), outline=(225, 226, 218), width=2)
    draw.line((104, 110, 104, PAGE_HEIGHT - 80), fill=MARGIN_RULE, width=3)
    for y in range(154, PAGE_HEIGHT - 80, LINE_HEIGHT):
        draw.line((66, y, PAGE_WIDTH - 64, y), fill=RULE, width=1)


def _draw_header(
    draw: ImageDraw.ImageDraw,
    header_font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
    page_number: int,
    total_pages: int,
) -> None:
    draw.text((MARGIN_LEFT, 74), "Assignment", font=header_font, fill=INK)
    page_label = f"Page {page_number}/{total_pages}"
    label_width = draw.textlength(page_label, font=small_font)
    draw.text((PAGE_WIDTH - MARGIN_RIGHT - label_width, 86), page_label, font=small_font, fill=(76, 89, 112))


def _draw_body(draw: ImageDraw.ImageDraw, page_text: str, font: ImageFont.ImageFont, page_number: int) -> None:
    rng = random.Random(f"fallback-page-{page_number}-{len(page_text)}")
    max_width = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    y = TOP_START

    for paragraph in page_text.split("\n\n"):
        wrapped_lines = _wrap_text(draw, paragraph.strip(), font, max_width)
        if not wrapped_lines:
            y += LINE_HEIGHT
            continue
        for line in wrapped_lines:
            if y > BOTTOM_LIMIT:
                return
            x_jitter = rng.randint(-3, 4)
            y_jitter = rng.randint(-2, 2)
            color = _vary_ink(rng)
            draw.text((MARGIN_LEFT + x_jitter, y - 31 + y_jitter), line, font=font, fill=color)
            y += LINE_HEIGHT
        y += int(LINE_HEIGHT * 0.45)


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    for raw_line in text.splitlines() or [text]:
        words = raw_line.split()
        current: list[str] = []
        for word in words:
            candidate = " ".join(current + [word])
            if current and draw.textlength(candidate, font=font) > max_width:
                lines.append(" ".join(current))
                current = [word]
            elif draw.textlength(word, font=font) > max_width:
                lines.extend(_break_long_word(draw, word, font, max_width))
                current = []
            else:
                current.append(word)
        if current:
            lines.append(" ".join(current))
    return lines


def _break_long_word(
    draw: ImageDraw.ImageDraw,
    word: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    chunks: list[str] = []
    current = ""
    for char in word:
        candidate = current + char
        if current and draw.textlength(candidate, font=font) > max_width:
            chunks.append(current)
            current = char
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks or textwrap.wrap(word, width=32)


def _vary_ink(rng: random.Random) -> tuple[int, int, int]:
    return tuple(max(0, min(255, channel + rng.randint(-7, 5))) for channel in INK)
