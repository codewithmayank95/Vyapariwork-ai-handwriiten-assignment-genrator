from __future__ import annotations

from pathlib import Path

from PIL import Image


A4_SIZE = (1240, 1754)


def build_pdf_from_images(image_paths: list[Path], output_path: Path) -> Path:
    if not image_paths:
        raise ValueError("No page images were generated.")

    pages: list[Image.Image] = []
    try:
        for image_path in image_paths:
            with Image.open(image_path) as source:
                page = _fit_to_a4(source.convert("RGB"))
                pages.append(page)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        first, rest = pages[0], pages[1:]
        first.save(output_path, "PDF", resolution=150.0, save_all=True, append_images=rest)
        return output_path
    finally:
        for page in pages:
            page.close()


def _fit_to_a4(image: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", A4_SIZE, "white")
    image.thumbnail(A4_SIZE, Image.Resampling.LANCZOS)
    left = (A4_SIZE[0] - image.width) // 2
    top = (A4_SIZE[1] - image.height) // 2
    canvas.paste(image, (left, top))
    return canvas
