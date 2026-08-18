"""Interview history entries for progress across mock sessions.

History lives in Streamlit session state (preserved across Reset / New Interview).
It is not a shared server file — Cloud users do not see each other's runs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

HISTORY_MAX_ENTRIES = 20


def _json_fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_history_entry(
    *,
    mode: str,
    role_label: str,
    job_description: str,
    duration_minutes: int,
    evaluation_results: dict[str, Any],
    turn_evaluations: list[dict[str, Any]],
    chat_history: list[dict[str, str]],
    answer_count: int,
    security_terminated: bool = False,
    completed_at: str | None = None,
) -> dict[str, Any]:
    """Build one completed-interview record (also used as a report payload)."""
    results = dict(evaluation_results or {})
    turns = [dict(t) for t in (turn_evaluations or [])]
    transcript = [
        {"role": m.get("role", ""), "content": m.get("content", "")}
        for m in (chat_history or [])
        if (m.get("content") or "").strip()
    ]
    when = completed_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    fingerprint = _json_fingerprint(
        {
            "mode": mode,
            "job_description": (job_description or "").strip(),
            "duration_minutes": int(duration_minutes or 0),
            "transcript": transcript,
        }
    )
    return {
        "id": f"il_{fingerprint}",
        "fingerprint": fingerprint,
        "completed_at": when,
        "mode": mode or "Behavioral",
        "role_label": role_label or "Mock Interview",
        "job_description": job_description or "",
        "duration_minutes": int(duration_minutes or 0),
        "overall_score": int(results.get("overall_score") or 0),
        "dimension_scores": dict(results.get("dimension_scores") or {}),
        "strengths": list(results.get("strengths") or []),
        "improvements": list(results.get("improvements") or []),
        "sample_answer": str(results.get("sample_answer") or ""),
        "turn_evaluations": turns,
        "chat_history": transcript,
        "answer_count": int(answer_count or 0),
        "security_terminated": bool(security_terminated or results.get("security_terminated")),
    }


def upsert_history_entry(
    history: list[dict[str, Any]],
    entry: dict[str, Any],
    *,
    max_entries: int = HISTORY_MAX_ENTRIES,
) -> list[dict[str, Any]]:
    """Append or replace by fingerprint; keep the newest ``max_entries`` items."""
    fingerprint = entry.get("fingerprint")
    kept = [item for item in history if item.get("fingerprint") != fingerprint]
    kept.append(entry)
    return kept[-max_entries:]


def history_score_series(history: list[dict[str, Any]]) -> list[int]:
    """Overall scores in chronological order for a simple progress chart."""
    return [int(item.get("overall_score") or 0) for item in history]
