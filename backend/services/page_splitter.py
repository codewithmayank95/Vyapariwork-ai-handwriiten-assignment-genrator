from __future__ import annotations

import re


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def split_text_into_pages(text: str, char_limit: int = 1250) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []

    pages: list[str] = []
    current: list[str] = []
    current_length = 0

    for block in _iter_blocks(normalized, char_limit):
        addition = len(block) + (2 if current else 0)
        if current and current_length + addition > char_limit:
            pages.append("\n\n".join(current).strip())
            current = [block]
            current_length = len(block)
        else:
            current.append(block)
            current_length += addition

    if current:
        pages.append("\n\n".join(current).strip())

    return [page for page in pages if page]


def _iter_blocks(text: str, char_limit: int) -> list[str]:
    blocks: list[str] = []
    for paragraph in [part.strip() for part in text.split("\n\n") if part.strip()]:
        if len(paragraph) <= char_limit:
            blocks.append(paragraph)
            continue
        blocks.extend(_split_long_paragraph(paragraph, char_limit))
    return blocks


def _split_long_paragraph(paragraph: str, char_limit: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    sentences = _SENTENCE_END.split(paragraph)
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(sentence) > char_limit:
            for word_chunk in _split_by_words(sentence, char_limit):
                chunks.append(word_chunk)
            current = []
            current_length = 0
            continue

        addition = len(sentence) + (1 if current else 0)
        if current and current_length + addition > char_limit:
            chunks.append(" ".join(current).strip())
            current = [sentence]
            current_length = len(sentence)
        else:
            current.append(sentence)
            current_length += addition

    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def _split_by_words(text: str, char_limit: int) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0
    for word in text.split():
        addition = len(word) + (1 if current else 0)
        if current and current_length + addition > char_limit:
            chunks.append(" ".join(current).strip())
            current = [word]
            current_length = len(word)
        else:
            current.append(word)
            current_length += addition
    if current:
        chunks.append(" ".join(current).strip())
    return chunks
