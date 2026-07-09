"""
English-language checks for InterviewLab voice interviews.
"""

from __future__ import annotations

import re

# Shown in the UI when transcription is not English.
NON_ENGLISH_UI_MESSAGE = (
    "Please respond in English. This mock interview is English-only to help you "
    "practice for English-language interviews."
)

# Interviewer reminder appended to chat when a non-English answer is detected.
NON_ENGLISH_INTERVIEWER_REMINDER = (
    "I noticed your response wasn't in English. This session is English-only — "
    "please answer in English so we can continue. Take your time, and I'll repeat "
    "the question when you're ready."
)

# Unicode ranges for common non-English scripts.
_NON_ENGLISH_SCRIPT = re.compile(
    r"[\u0400-\u04FF"  # Cyrillic
    r"\u0600-\u06FF"  # Arabic
    r"\u0900-\u097F"  # Devanagari
    r"\u3040-\u30FF"  # Japanese kana
    r"\u4E00-\u9FFF"  # CJK
    r"\uAC00-\uD7AF"  # Korean
    r"\u0E00-\u0E7F"  # Thai
    r"\u0370-\u03FF]"  # Greek
)

# Common non-English words/phrases (lightweight heuristic for Latin-script languages).
_NON_ENGLISH_PHRASES = re.compile(
    r"\b("
    r"bonjour|merci|salut|gracias|hola|buenos|por favor|"
    r"danke|bitte|guten|ich bin|"
    r"obrigado|obrigada|bom dia|"
    r"ni hao|xie xie|"
    r"annyeong|gamsahamnida"
    r")\b",
    re.IGNORECASE,
)


def is_english_text(text: str) -> bool:
    """Return True when the answer appears to be English."""
    cleaned = (text or "").strip()
    if not cleaned:
        return False

    if _NON_ENGLISH_SCRIPT.search(cleaned):
        return False

    if _NON_ENGLISH_PHRASES.search(cleaned):
        return False

    # Mostly Latin letters, numbers, and punctuation.
    latin_chars = len(re.findall(r"[A-Za-z]", cleaned))
    letter_chars = len(re.findall(r"\w", cleaned, flags=re.UNICODE))
    if letter_chars == 0:
        return True
    return latin_chars / letter_chars >= 0.85
