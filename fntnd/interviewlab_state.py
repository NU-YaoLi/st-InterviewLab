"""
Session state helpers for InterviewLab.

- ``init_session_state``: defaults for every key the UI reads.
- ``state_from_session`` / ``apply_state_to_session``: map between
  ``st.session_state`` and ``InterviewState`` without coupling backend logic
  to Streamlit.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from bknd.interviewlab_engine import InterviewState
from interviewlab_config import DEFAULT_DURATION_MINUTES, SESSION_DEFAULTS, TOTAL_QUESTIONS


def init_session_state() -> None:
    """Seed all required keys once per browser session."""
    for key, default in SESSION_DEFAULTS.items():
        st.session_state.setdefault(key, default)


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
    """Return the OpenAI API key from Streamlit secrets or session fallback."""
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

    return (st.session_state.get("openai_api_key") or "").strip()


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
        input_mode=session.get("input_mode", "Audio + Text"),
        ai_voice_enabled=session.get("ai_voice_enabled", False),
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
        last_tts_audio=session.get("last_tts_audio"),
        error_message=session.get("error_message"),
        interview_duration_minutes=session.get(
            "interview_duration_minutes", DEFAULT_DURATION_MINUTES
        ),
        interview_started_at=session.get("interview_started_at"),
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
    session["input_mode"] = state.input_mode
    session["ai_voice_enabled"] = state.ai_voice_enabled
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
    session["last_tts_audio"] = state.last_tts_audio
    session["error_message"] = state.error_message
    session["interview_duration_minutes"] = state.interview_duration_minutes
    session["interview_started_at"] = state.interview_started_at


def reset_runtime_session() -> None:
    """Reset interview runtime while preserving setup + API key."""
    preserved = {
        "interview_mode": st.session_state.get("interview_mode"),
        "target_role": st.session_state.get("target_role"),
        "target_level": st.session_state.get("target_level"),
        "job_description": st.session_state.get("job_description"),
        "resume": st.session_state.get("resume"),
        "input_mode": st.session_state.get("input_mode"),
        "interview_duration_minutes": st.session_state.get(
            "interview_duration_minutes", DEFAULT_DURATION_MINUTES
        ),
    }
    for key, default in SESSION_DEFAULTS.items():
        st.session_state[key] = default
    st.session_state.update(preserved)
