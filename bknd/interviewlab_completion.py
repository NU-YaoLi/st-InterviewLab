"""Detect when the interviewer has verbally concluded the mock interview."""

from __future__ import annotations

import re

# Prefer an exact closing line in Realtime instructions; heuristics catch variants.
_EXACT_PHRASES = (
    "this interview has concluded",
    "the interview has concluded",
    "that concludes our interview",
    "that concludes the interview",
    "that concludes this interview",
    "this mock interview has concluded",
    "the mock interview has concluded",
)

_END_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\binterview\s+has\s+concluded\b", re.IGNORECASE),
    re.compile(r"\bthat\s+concludes\s+(our|the|this)\s+(mock\s+)?interview\b", re.IGNORECASE),
    re.compile(r"\b(we('re| are)\s+)?(all\s+)?(done|finished)\s+(with\s+)?(the\s+)?(mock\s+)?interview\b", re.IGNORECASE),
    re.compile(r"\b(wrap(?:s|ping)?\s+up|that\s+wraps\s+up)\s+(our|the|this)\s+(session|interview)\b", re.IGNORECASE),
    re.compile(r"\bend(s|ing)?\s+(our|the|this)\s+(mock\s+)?interview\b", re.IGNORECASE),
    re.compile(
        r"\bthank\s+you\s+for\s+(your\s+)?(time|participat\w+)\b.*\b(concluded|goodbye|good\s+luck|wrap)",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"\b(concluded|goodbye|good\s+luck)\b.*\bthank\s+you\s+for\s+(your\s+)?(time|participat\w+)\b",
        re.IGNORECASE | re.DOTALL,
    ),
)


def looks_like_interview_end(text: str) -> bool:
    """
    Return True when interviewer speech clearly signals the session is over.

    Used by Python finalize triggers and mirrored loosely in the JS bridge.
    Prefer precision: casual "thanks" mid-interview must not auto-end.
    """
    cleaned = (text or "").strip()
    if len(cleaned) < 12:
        return False

    lower = cleaned.lower()
    for phrase in _EXACT_PHRASES:
        if phrase in lower:
            return True

    for pattern in _END_PATTERNS:
        if pattern.search(cleaned):
            return True

    # Soft wrap-up: thank-you + goodbye/good luck in a short closing turn.
    if len(cleaned.split()) <= 60:
        thanks = "thank you" in lower or "thanks for your time" in lower
        closing = any(
            cue in lower
            for cue in (
                "goodbye",
                "good bye",
                "good luck",
                "best of luck",
                "we'll be in touch",
                "we will be in touch",
                "that's all for today",
                "that is all for today",
            )
        )
        if thanks and closing:
            return True

    return False
