"""Active interview view — Zoom-style English voice meeting."""

from __future__ import annotations

import base64
import hashlib
import html
import time

import streamlit as st
import streamlit.components.v1 as components

from bknd.interviewlab_audio import generate_speech, synthesize_if_enabled, transcribe_audio_bytes
from bknd.interviewlab_engine import (
    begin_live_session,
    end_interview_manually,
    force_close_interview,
    format_remaining_time,
    get_progress_fraction,
    get_remaining_seconds,
    is_time_expired,
    process_user_response,
)
from bknd.interviewlab_evaluator import run_evaluation
from bknd.interviewlab_language import NON_ENGLISH_UI_MESSAGE, is_english_text
from bknd.interviewlab_openai import get_openai_client
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_state import apply_state_to_session, get_job_display_label, state_from_session
from interviewlab_config import PER_TURN_EVALUATION


def render_chat_history() -> None:
    """Full transcript for post-interview review."""
    for msg in st.session_state.get("chat_history", []):
        role = "assistant" if msg["role"] == "assistant" else "user"
        avatar = "🎤" if role == "assistant" else "👤"
        with st.chat_message(role, avatar=avatar):
            st.markdown(msg["content"])


def _estimate_speech_seconds(text: str) -> float:
    words = len(text.split())
    return max(3.0, min(45.0, words * 0.42))


def _set_live_caption(speaker: str, text: str, *, duration: float | None = None) -> None:
    st.session_state["live_caption_speaker"] = speaker
    st.session_state["live_caption_text"] = text
    st.session_state["active_speaker"] = speaker
    if duration is not None:
        st.session_state["live_caption_expires_at"] = time.time() + duration
    else:
        st.session_state["live_caption_expires_at"] = None


def _clear_live_caption() -> None:
    st.session_state["live_caption_text"] = None
    st.session_state["live_caption_speaker"] = None
    st.session_state["live_caption_expires_at"] = None
    st.session_state["active_speaker"] = None


def _expire_live_caption_if_needed() -> None:
    expires = st.session_state.get("live_caption_expires_at")
    if expires and time.time() > expires:
        _clear_live_caption()


def _timer_class(remaining_seconds: float) -> str:
    if remaining_seconds <= 60:
        return "interview-timer interview-timer-critical"
    if remaining_seconds <= 180:
        return "interview-timer interview-timer-warning"
    return "interview-timer"


def _read_audio_input(key: str = "candidate_audio") -> bytes | None:
    if not hasattr(st, "audio_input"):
        return None

    audio_value = st.audio_input(
        "Record your answer in English",
        key=key,
        label_visibility="collapsed",
    )
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


def _play_tts_autoplay(audio_bytes: bytes | None, caption_text: str = "") -> None:
    """Play interviewer audio and keep caption visible for estimated speech duration."""
    if not audio_bytes:
        return
    b64 = base64.b64encode(audio_bytes).decode()
    components.html(
        f"""
        <audio autoplay playsinline style="display:none">
            <source src="data:audio/mpeg;base64,{b64}" type="audio/mpeg">
        </audio>
        """,
        height=0,
    )
    if caption_text:
        _set_live_caption("interviewer", caption_text, duration=_estimate_speech_seconds(caption_text))


def _render_meeting_room() -> None:
    active = st.session_state.get("active_speaker")
    interviewer_cls = "participant-tile speaking" if active == "interviewer" else "participant-tile"
    you_cls = "participant-tile speaking" if active == "you" else "participant-tile"

    interviewer_status = "Speaking…" if active == "interviewer" else "Interviewer"
    you_status = "Speaking…" if active == "you" else "You"

    st.markdown(
        f"""
        <div class="meeting-room">
            <div class="meeting-participants">
                <div class="{interviewer_cls}">
                    <div class="participant-avatar">🎤</div>
                    <div class="participant-name">Interviewer</div>
                    <div class="participant-status">{interviewer_status}</div>
                </div>
                <div class="{you_cls}">
                    <div class="participant-avatar">👤</div>
                    <div class="participant-name">You</div>
                    <div class="participant-status">{you_status}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_live_caption() -> None:
    _expire_live_caption_if_needed()
    text = st.session_state.get("live_caption_text")
    speaker = st.session_state.get("live_caption_speaker")
    if not text or not speaker:
        return

    label = "Interviewer" if speaker == "interviewer" else "You"
    safe_text = html.escape(text)
    st.markdown(
        f"""
        <div class="live-caption-bar">
            <div class="live-caption-speaker">{label}</div>
            <div class="live-caption-text">{safe_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.fragment(run_every=2)
def _timer_fragment(api_key: str) -> None:
    """Auto-refresh timer and expire live captions."""
    _expire_live_caption_if_needed()

    if not st.session_state.get("interview_session_started"):
        return

    state = state_from_session(st.session_state)
    if not st.session_state.get("interview_active"):
        return

    remaining = get_remaining_seconds(state)
    timer_cls = _timer_class(remaining)
    mode = st.session_state.get("interview_mode", "Behavioral")
    role = get_job_display_label(st.session_state)
    duration = st.session_state.get("interview_duration_minutes", 20)

    end_col, header_col = st.columns([1, 4])
    with end_col:
        if st.button("End Interview", type="secondary", use_container_width=True):
            st.session_state["_end_interview_requested"] = True
    with header_col:
        st.markdown(
            f"""
            <div class="interview-header">
                <div>
                    <div class="interview-header-title">{mode} Interview · {role}</div>
                    <div class="status-badge" style="margin-top:0.5rem">
                        <span class="status-dot"></span> Live · English voice
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

    if st.session_state.pop("_end_interview_requested", False):
        _handle_end_interview(api_key)
        return

    if is_time_expired(state):
        _handle_time_expiry(api_key, state)
        return

    _render_meeting_room()
    _render_live_caption()


def _render_ready_header() -> None:
    mode = st.session_state.get("interview_mode", "Behavioral")
    role = get_job_display_label(st.session_state)
    duration = st.session_state.get("interview_duration_minutes", 20)

    st.markdown(
        f"""
        <div class="interview-header">
            <div>
                <div class="interview-header-title">{mode} Interview · {role}</div>
                <div class="status-badge" style="margin-top:0.5rem">
                    Ready · English voice
                </div>
            </div>
            <div style="text-align:right">
                <div class="interview-timer">{duration:02d}:00</div>
                <div style="font-size:0.8rem;opacity:0.7;margin-top:0.25rem">
                    Press Start when you're ready
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _handle_time_expiry(api_key: str, state) -> None:
    if not is_time_expired(state):
        return

    try:
        client = get_openai_client(api_key)
        force_close_interview(state, client)
        with st.spinner("Generating your evaluation…"):
            run_evaluation(client, state)
        _clear_live_caption()
        apply_state_to_session(state, st.session_state)
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)


def _handle_end_interview(api_key: str) -> None:
    state = state_from_session(st.session_state)
    try:
        client = get_openai_client(api_key)
        with st.spinner("Ending interview…"):
            end_interview_manually(state, client)
            run_evaluation(client, state)
        _clear_live_caption()
        apply_state_to_session(state, st.session_state)
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)


def _process_answer(api_key: str, user_answer: str) -> None:
    state = state_from_session(st.session_state)
    try:
        client = get_openai_client(api_key)
        _clear_live_caption()

        with st.spinner("Interviewer is thinking…"):
            result = process_user_response(state, client, user_answer)

        _clear_live_caption()

        if PER_TURN_EVALUATION and result.get("user_answer") and state.responses:
            with st.spinner("Evaluating your response…"):
                run_evaluation(
                    client,
                    state,
                    per_turn=True,
                    latest_question=state.responses[-1]["question"],
                    latest_answer=result["user_answer"],
                )

        message = result.get("message", "")
        if message:
            state.last_tts_audio = synthesize_if_enabled(
                client, message, state.ai_voice_enabled
            )
            if state.last_tts_audio:
                st.session_state["_autoplay_tts"] = True
                st.session_state["_autoplay_caption"] = message

        if result.get("action") == "complete":
            with st.spinner("Generating your evaluation…"):
                run_evaluation(client, state)

        apply_state_to_session(state, st.session_state)
        st.rerun()

    except Exception as exc:
        _clear_live_caption()
        display_openai_error(exc)


def _handle_begin_session(api_key: str) -> None:
    state = state_from_session(st.session_state)
    try:
        client = get_openai_client(api_key)
        begin_live_session(state)

        if state.chat_history:
            last_message = state.chat_history[-1]["content"]
            state.last_tts_audio = generate_speech(client, last_message)
            st.session_state["_autoplay_caption"] = last_message

        apply_state_to_session(state, st.session_state)
        st.session_state["_autoplay_tts"] = True
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)


def render_interview_view(api_key: str) -> None:
    session_started = st.session_state.get("interview_session_started", False)

    if session_started and st.session_state.pop("_autoplay_tts", False):
        audio = st.session_state.get("last_tts_audio")
        caption = st.session_state.pop("_autoplay_caption", "")
        if audio:
            _play_tts_autoplay(audio, caption)
            st.session_state["last_tts_audio"] = None

    if session_started:
        _timer_fragment(api_key)
    else:
        _render_ready_header()
        _render_meeting_room()

    if not session_started:
        st.markdown(
            '<p class="meeting-idle-hint">'
            'When you start, the interviewer will speak automatically. '
            'Live captions appear only while someone is speaking.</p>',
            unsafe_allow_html=True,
        )
        if st.button("Start Interview", type="primary", use_container_width=True):
            _handle_begin_session(api_key)
        return

    st.markdown(
        '<p style="color:#64748b;font-size:0.85rem;text-align:center;margin:0.75rem 0">'
        '🎙️ Tap the microphone below to record your answer in English</p>',
        unsafe_allow_html=True,
    )

    _render_voice_input(api_key)


def _render_voice_input(api_key: str) -> None:
    if not hasattr(st, "audio_input"):
        st.error(
            "Voice interviews require Streamlit >= 1.33 with microphone support. "
            "Please upgrade Streamlit and allow microphone access in your browser."
        )
        return

    audio_bytes = _read_audio_input()

    if not audio_bytes:
        return

    audio_hash = _audio_hash(audio_bytes)
    last_hash = st.session_state.get("last_audio_hash")

    if audio_hash == last_hash:
        return

    st.session_state["last_audio_hash"] = audio_hash
    _set_live_caption("you", "Processing your response…", duration=15.0)

    try:
        client = get_openai_client(api_key)
        with st.spinner("Transcribing your response…"):
            transcribed = transcribe_audio_bytes(client, audio_bytes)
        if not transcribed.strip():
            _clear_live_caption()
            st.warning("Couldn't detect speech. Please try again and speak clearly in English.")
            return

        _set_live_caption("you", transcribed, duration=4.0)

        if not is_english_text(transcribed):
            st.warning(NON_ENGLISH_UI_MESSAGE)
            _process_answer(api_key, transcribed)
            return
        _process_answer(api_key, transcribed)
    except Exception as exc:
        _clear_live_caption()
        display_openai_error(exc)
