from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any

from ..config import Settings


class GeminiImageError(RuntimeError):
    pass


class GeminiImageService:
    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise GeminiImageError("GEMINI_API_KEY is not configured.")
        self.settings = settings
        self._genai, self._types, self._errors = self._load_sdk()
        self._client = self._genai.Client(api_key=settings.gemini_api_key)

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()

    def generate_page_image(self, page_text: str, page_number: int, total_pages: int, output_path: Path) -> Path:
        prompt = _build_prompt(page_text, page_number, total_pages)
        last_error: Exception | None = None

        for attempt in range(self.settings.image_retry_count + 1):
            try:
                response = self._client.models.generate_content(
                    model=self.settings.gemini_image_model,
                    contents=[prompt],
                    config=self._types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=self._types.ImageConfig(aspect_ratio="3:4"),
                    ),
                )
                self._save_first_image(response, output_path)
                return output_path
            except Exception as exc:
                last_error = exc
                if attempt >= self.settings.image_retry_count or not self._is_retryable(exc):
                    break
                delay = self.settings.image_retry_delay_seconds * (attempt + 1)
                time.sleep(delay)

        raise GeminiImageError(f"Gemini image generation failed: {last_error}") from last_error

    def _save_first_image(self, response: Any, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        for part in _response_parts(response):
            inline_data = getattr(part, "inline_data", None)
            if not inline_data:
                continue

            as_image = getattr(part, "as_image", None)
            if callable(as_image):
                image = as_image()
                image.save(output_path)
                return

            data = getattr(inline_data, "data", None)
            if data:
                if isinstance(data, str):
                    data = base64.b64decode(data)
                output_path.write_bytes(data)
                return

        raise GeminiImageError("Gemini response did not include an image.")

    def _is_retryable(self, exc: Exception) -> bool:
        api_error = getattr(self._errors, "APIError", None)
        if api_error and isinstance(exc, api_error):
            code = getattr(exc, "code", None)
            return code in {429, 500, 502, 503, 504}
        message = str(exc).lower()
        return any(token in message for token in ("rate", "quota", "resource_exhausted", "temporarily"))

    @staticmethod
    def _load_sdk() -> tuple[Any, Any, Any]:
        try:
            from google import genai
            from google.genai import errors, types
        except Exception as exc:
            raise GeminiImageError("Install google-genai to enable AI image generation.") from exc
        return genai, types, errors


def _response_parts(response: Any) -> list[Any]:
    direct_parts = getattr(response, "parts", None)
    if direct_parts:
        return list(direct_parts)

    parts: list[Any] = []
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        if content:
            parts.extend(getattr(content, "parts", []) or [])
    return parts


def _build_prompt(page_text: str, page_number: int, total_pages: int) -> str:
    return f"""
Create a single realistic portrait A4 student handwritten assignment page image.

Style requirements:
- Blue pen ink.
- Cursive but readable handwriting.
- Ruled notebook paper with a clean red left margin.
- Text aligned neatly on notebook lines.
- Professional college assignment style.
- Natural pen pressure and small handwriting variation.
- No extra diagrams, stickers, logos, or decorative borders.

Page context: page {page_number} of {total_pages}.

Write this exact assignment text in order. Preserve spelling, punctuation, headings, and line breaks as much as an image model can:
<<<
{page_text}
>>>
""".strip()
