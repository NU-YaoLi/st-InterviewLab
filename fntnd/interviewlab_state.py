"""
Session state helpers for InterviewLab.

- ``init_session_state``: defaults for every key the UI reads.
- ``state_from_session`` / ``apply_state_to_session``: map between
  ``st.session_state`` and ``InterviewState`` without coupling backend logic
  to Streamlit.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any

import streamlit as st

from bknd.interviewlab_engine import InterviewState
from bknd.interviewlab_history import build_history_entry, upsert_history_entry
from interviewlab_config import DEFAULT_DURATION_MINUTES, SESSION_DEFAULTS, TOTAL_QUESTIONS


def init_session_state() -> None:
    """Seed all required keys once per browser session."""
    for key, default in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, copy.deepcopy(default))


def get_job_display_label(session: dict | Any = None) -> str:
    """Short label for the job from session job details."""
    if session is None:
        session = st.session_state
    details = (session.get("job_description") or "").strip()
    if not details:
        return "Mock Interview"
    first_line = details.splitlines()[0].strip()
    if len(first_line) > 48:
        return first_line[:45] + "…"
    return first_line or "Mock Interview"


def get_api_key_from_session() -> str:
    """Return the OpenAI API key from Streamlit secrets only."""
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return str(key).strip()
    except (AttributeError, FileNotFoundError, KeyError):
        pass

    try:
        openai_secrets = st.secrets.get("openai", {})
        if isinstance(openai_secrets, dict):
            key = openai_secrets.get("api_key", "")
            if key:
                return str(key).strip()
    except (AttributeError, FileNotFoundError, KeyError):
        pass

    return ""


def state_from_session(session: dict[str, Any] | Any) -> InterviewState:
    """Build ``InterviewState`` from a session_state-like mapping."""
    return InterviewState(
        interview_active=session.get("interview_active", False),
        interview_complete=session.get("interview_complete", False),
        interview_mode=session.get("interview_mode", "Behavioral"),
        target_role=session.get("target_role", ""),
        target_level=session.get("target_level", ""),
        job_description=session.get("job_description", ""),
        resume=session.get("resume", ""),
        chat_history=list(session.get("chat_history", [])),
        current_question_index=session.get("current_question_index", 0),
        total_questions=session.get("total_questions", TOTAL_QUESTIONS),
        current_question_text=session.get("current_question_text", ""),
        responses=list(session.get("responses", [])),
        awaiting_follow_up=session.get("awaiting_follow_up", False),
        follow_up_count=session.get("follow_up_count", 0),
        scores=session.get("scores"),
        evaluation_results=session.get("evaluation_results"),
        turn_evaluations=list(session.get("turn_evaluations", [])),
        error_message=session.get("error_message"),
        interview_duration_minutes=session.get(
            "interview_duration_minutes", DEFAULT_DURATION_MINUTES
        ),
        interview_started_at=session.get("interview_started_at"),
        interview_session_started=session.get("interview_session_started", False),
    )


def apply_state_to_session(state: InterviewState, session: dict[str, Any] | Any) -> None:
    """Write ``InterviewState`` back into session_state."""
    session["interview_active"] = state.interview_active
    session["interview_complete"] = state.interview_complete
    session["interview_mode"] = state.interview_mode
    session["target_role"] = state.target_role
    session["target_level"] = state.target_level
    session["job_description"] = state.job_description
    session["resume"] = state.resume
    session["chat_history"] = state.chat_history
    session["current_question_index"] = state.current_question_index
    session["total_questions"] = state.total_questions
    session["current_question_text"] = state.current_question_text
    session["responses"] = state.responses
    session["awaiting_follow_up"] = state.awaiting_follow_up
    session["follow_up_count"] = state.follow_up_count
    session["scores"] = state.scores
    session["evaluation_results"] = state.evaluation_results
    session["turn_evaluations"] = state.turn_evaluations
    session["error_message"] = state.error_message
    session["interview_duration_minutes"] = state.interview_duration_minutes
    session["interview_started_at"] = state.interview_started_at
    session["interview_session_started"] = state.interview_session_started


def reset_runtime_session() -> None:
    """Reset interview runtime while preserving setup fields and history."""
    preserved = {
        "interview_mode": st.session_state.get("interview_mode"),
        "target_role": st.session_state.get("target_role"),
        "target_level": st.session_state.get("target_level"),
        "job_description": st.session_state.get("job_description"),
        "resume": st.session_state.get("resume"),
        "resume_typed": st.session_state.get("resume_typed"),
        "resume_file_text": st.session_state.get("resume_file_text"),
        "resume_file_name": st.session_state.get("resume_file_name"),
        "resume_file_hash": st.session_state.get("resume_file_hash"),
        "interview_duration_minutes": st.session_state.get(
            "interview_duration_minutes", DEFAULT_DURATION_MINUTES
        ),
        "interview_history": list(st.session_state.get("interview_history") or []),
    }
    for key, default in SESSION_DEFAULTS.items():
        st.session_state[key] = copy.deepcopy(default)
    st.session_state.update(preserved)


def record_completed_interview(session: dict[str, Any] | Any = None) -> dict[str, Any]:
    """Store the current evaluation in interview history (fingerprint-deduped)."""
    if session is None:
        session = st.session_state
    results = session.get("evaluation_results") or {}
    if not results:
        return {}

    completed_at = session.get("interview_completed_at") or datetime.now(
        timezone.utc
    ).isoformat(timespec="seconds")
    session["interview_completed_at"] = completed_at
    responses = [
        r for r in (session.get("responses") or []) if (r.get("answer") or "").strip()
    ]
    answer_count = len(responses) or sum(
        1
        for m in (session.get("chat_history") or [])
        if m.get("role") == "user" and (m.get("content") or "").strip()
    )
    entry = build_history_entry(
        mode=session.get("interview_mode") or "Behavioral",
        role_label=get_job_display_label(session),
        job_description=session.get("job_description") or "",
        duration_minutes=int(
            session.get("interview_duration_minutes") or DEFAULT_DURATION_MINUTES
        ),
        evaluation_results=results,
        turn_evaluations=list(session.get("turn_evaluations") or []),
        chat_history=list(session.get("chat_history") or []),
        answer_count=answer_count,
        security_terminated=bool(
            session.get("security_terminated") or results.get("security_terminated")
        ),
        completed_at=completed_at,
    )
    session["interview_history"] = upsert_history_entry(
        list(session.get("interview_history") or []),
        entry,
    )
    return entry
