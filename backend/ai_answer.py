from __future__ import annotations

import random
import re
from typing import List

from config import SETTINGS


WORD_TARGETS = {
    "short": 120,
    "medium": 250,
    "long": 450,
}


def _normalize_length(value: str) -> str:
    v = (value or "").strip().lower()
    return v if v in WORD_TARGETS else "medium"


def _word_count(text: str) -> int:
    return len(re.findall(r"\\b\\w+\\b", text))


def _fallback_answer(question: str, target_words: int) -> str:
    clean_q = question.strip()
    if not clean_q:
        clean_q = "Explain the topic."

    title = clean_q
    if len(title) > 90:
        title = title[:87].rstrip() + "..."

    parts: list[str] = []
    parts.append(f"Title: {title}")
    parts.append("")
    parts.append("Definition:")
    parts.append(
        "This topic refers to the main concept asked in the question. It explains the meaning, purpose, and basic idea in a clear way."
    )
    parts.append("")
    parts.append("Explanation:")
    parts.append(
        "First, we understand the background and why the concept is important in practical situations. Then we describe how it works step by step and what results it produces."
    )
    parts.append(
        "In exams, it is best to write the core meaning, give a simple explanation, and connect it with real-world applications."
    )
    parts.append("")
    parts.append("Key Points:")
    key_points = [
        "It has a clear purpose and solves a specific problem.",
        "It follows a defined process or set of rules.",
        "It improves understanding, accuracy, or efficiency when applied correctly.",
        "It is widely used in academics and industry in different forms.",
        "It has advantages and limitations depending on the situation.",
    ]
    random.shuffle(key_points)
    for idx, kp in enumerate(key_points[:4], start=1):
        parts.append(f"{idx}) {kp}")
    parts.append("")
    parts.append("Conclusion:")
    parts.append(
        "In conclusion, the concept can be summarized by its meaning and working. A well-structured answer should include definition, explanation, key points, and a final summary."
    )

    text = "\n".join(parts).strip() + "\n"

    # Pad gently to reach target length
    filler = [
        "Additionally, understanding the basic terms helps to write correct answers in exams.",
        "A simple example can be used to make the explanation easier to understand.",
        "When writing, focus on clarity, correct steps, and proper terminology.",
        "This topic is important because it builds the foundation for advanced concepts in the subject.",
    ]
    i = 0
    while _word_count(text) < target_words and i < 40:
        text += "\n" + filler[i % len(filler)]
        i += 1

    # Trim if too long
    words = text.split()
    if len(words) > int(target_words * 1.15):
        text = " ".join(words[: int(target_words * 1.10)]) + "\n"
    return text.strip()


def _try_gemini_answer(question: str, target_words: int) -> str | None:
    if not SETTINGS.gemini_api_key:
        return None

    try:
        import google.generativeai as genai  # type: ignore
    except Exception:
        return None

    genai.configure(api_key=SETTINGS.gemini_api_key)

    prompt = f"""
Write a college exam style answer in simple English.

Question: {question}

Requirements:
- Plain text only (no markdown symbols, no '*' or '-' bullets).
- Use headings exactly: Title, Definition, Explanation, Key Points, Conclusion.
- In Key Points, use numbering like 1) 2) 3) etc.
- Around {target_words} words (approximate is fine).
- Keep it readable and structured.
""".strip()

    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        text = getattr(resp, "text", None) or ""
        text = text.strip()
        if not text:
            return None
        return text
    except Exception:
        return None


def generate_answers(questions: List[str], answer_length: str) -> List[str]:
    length_key = _normalize_length(answer_length)
    target_words = WORD_TARGETS[length_key]

    answers: list[str] = []
    for q in questions:
        q_clean = (q or "").strip()
        if not q_clean:
            continue
        ai_text = _try_gemini_answer(q_clean, target_words)
        if ai_text is None:
            ai_text = _fallback_answer(q_clean, target_words)
        # Safety cleanup: remove stray markdown bullets if any slipped in
        ai_text = re.sub(r"^\\s*[-*]\\s+", "", ai_text, flags=re.MULTILINE).strip()
        answers.append(ai_text)
    return answers

