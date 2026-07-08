"""Active interview view with timer and streamlined input."""

from __future__ import annotations

import hashlib
import io

import streamlit as st

from bknd.interviewlab_audio import synthesize_if_enabled, transcribe_audio_bytes
from bknd.interviewlab_engine import (
    force_close_interview,
    format_remaining_time,
    get_progress_fraction,
    get_remaining_seconds,
    is_time_expired,
    process_user_response,
)
from bknd.interviewlab_evaluator import run_evaluation
from bknd.interviewlab_openai import get_openai_client
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_state import apply_state_to_session, state_from_session
from interviewlab_config import PER_TURN_EVALUATION


def render_chat_history() -> None:
    for msg in st.session_state.get("chat_history", []):
        role = "assistant" if msg["role"] == "assistant" else "user"
        avatar = "🎤" if role == "assistant" else "👤"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])


def _timer_class(remaining_seconds: float) -> str:
    if remaining_seconds <= 60:
        return "interview-timer interview-timer-critical"
    if remaining_seconds <= 180:
        return "interview-timer interview-timer-warning"
    return "interview-timer"


def _read_audio_input(key: str = "candidate_audio") -> bytes | None:
    if not hasattr(st, "audio_input"):
        return None

    audio_value = st.audio_input("Record your answer", key=key, label_visibility="collapsed")
    if audio_value is None:
        return None
    if hasattr(audio_value, "read"):
        audio_value.seek(0)
        return audio_value.read()
    if isinstance(audio_value, bytes):
        return audio_value
    return None


def _audio_hash(audio_bytes: bytes) -> str:
    return hashlib.md5(audio_bytes).hexdigest()


def _play_tts_once(audio_bytes: bytes | None) -> None:
    if audio_bytes:
        st.audio(io.BytesIO(audio_bytes), format="audio/mp3")


@st.fragment(run_every=1)
def _timer_fragment(api_key: str) -> None:
    """Auto-refresh timer display every second."""
    state = state_from_session(st.session_state)
    if not st.session_state.get("interview_active"):
        return

    remaining = get_remaining_seconds(state)
    timer_cls = _timer_class(remaining)
    mode = st.session_state.get("interview_mode", "Behavioral")
    role = st.session_state.get("target_role", "")
    duration = st.session_state.get("interview_duration_minutes", 20)

    st.markdown(
        f"""
        <div class="interview-header">
            <div>
                <div class="interview-header-title">{mode} Interview · {role}</div>
                <div class="status-badge" style="margin-top:0.5rem">
                    <span class="status-dot"></span> Live
                </div>
            </div>
            <div style="text-align:right">
                <div class="{timer_cls}">{format_remaining_time(state)}</div>
                <div style="font-size:0.8rem;opacity:0.7;margin-top:0.25rem">
                    {duration} min session
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    progress = get_progress_fraction(state)
    st.progress(progress, text=f"Session progress · {format_remaining_time(state)} remaining")

    if is_time_expired(state):
        _handle_time_expiry(api_key, state)


def _handle_time_expiry(api_key: str, state) -> bool:
    """Auto-close interview when timer hits zero. Returns True if expired."""
    if not is_time_expired(state):
        return False

    try:
        client = get_openai_client(api_key)
        force_close_interview(state, client)
        with st.spinner("Generating your evaluation…"):
            run_evaluation(client, state)
        apply_state_to_session(state, st.session_state)
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)
    return True


def _process_answer(api_key: str, user_answer: str) -> None:
    state = state_from_session(st.session_state)
    try:
        client = get_openai_client(api_key)

        with st.spinner("Interviewer is thinking…"):
            result = process_user_response(state, client, user_answer)

        if PER_TURN_EVALUATION and result.get("user_answer") and state.responses:
            with st.spinner("Evaluating your response…"):
                run_evaluation(
                    client,
                    state,
                    per_turn=True,
                    latest_question=state.responses[-1]["question"],
                    latest_answer=result["user_answer"],
                )

        if result.get("message"):
            state.last_tts_audio = synthesize_if_enabled(
                client, result["message"], state.ai_voice_enabled
            )

        if result.get("action") == "complete":
            with st.spinner("Generating your evaluation…"):
                run_evaluation(client, state)

        apply_state_to_session(state, st.session_state)
        st.rerun()

    except Exception as exc:
        display_openai_error(exc)


def render_interview_view(api_key: str) -> None:
    state = state_from_session(st.session_state)

    _timer_fragment(api_key)

    render_chat_history()

    if state.last_tts_audio:
        _play_tts_once(state.last_tts_audio)
        st.session_state["last_tts_audio"] = None

    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;text-align:center;margin:1rem 0">'
        'Respond naturally — type your answer or record audio below. '
        'The interview continues automatically after each response.</p>',
        unsafe_allow_html=True,
    )

    _render_response_input(api_key)


def _render_response_input(api_key: str) -> None:
    input_mode = st.session_state.get("input_mode", "Audio + Text")

    text_answer = st.chat_input("Type your answer here…")

    audio_bytes = None
    if input_mode == "Audio + Text":
        audio_bytes = _read_audio_input()

    if text_answer:
        _process_answer(api_key, text_answer)
        return

    if audio_bytes and input_mode == "Audio + Text":
        audio_hash = _audio_hash(audio_bytes)
        last_hash = st.session_state.get("last_audio_hash")

        if audio_hash != last_hash:
            st.session_state["last_audio_hash"] = audio_hash
            try:
                client = get_openai_client(api_key)
                with st.spinner("Transcribing your response…"):
                    transcribed = transcribe_audio_bytes(client, audio_bytes)
                if transcribed.strip():
                    _process_answer(api_key, transcribed)
                else:
                    st.warning("Couldn't detect speech. Please try again or type your answer.")
            except Exception as exc:
                display_openai_error(exc)
