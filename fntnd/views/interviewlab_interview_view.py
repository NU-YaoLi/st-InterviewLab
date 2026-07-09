"""Active interview view — Zoom-style English voice meeting."""

from __future__ import annotations

import base64
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
    get_remaining_seconds,
    is_time_expired,
    process_user_response,
)
from bknd.interviewlab_evaluator import run_evaluation
from bknd.interviewlab_language import NON_ENGLISH_UI_MESSAGE, is_english_text
from bknd.interviewlab_openai import get_openai_client
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_mic_component import render_auto_mic
from fntnd.interviewlab_state import apply_state_to_session, get_job_display_label, state_from_session
from interviewlab_config import PER_TURN_EVALUATION, SILENCE_SUBMIT_SECONDS


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
    speaker = st.session_state.get("live_caption_speaker")
    if expires and time.time() > expires:
        if (
            speaker == "interviewer"
            and st.session_state.get("interview_phase") == "interviewer_speaking"
        ):
            st.session_state["interview_phase"] = "listening"
        _clear_live_caption()


def _timer_class(remaining_seconds: float) -> str:
    if remaining_seconds <= 60:
        return "interview-timer interview-timer-critical"
    if remaining_seconds <= 180:
        return "interview-timer interview-timer-warning"
    return "interview-timer"


def _decode_mic_payload(payload: object) -> tuple[bytes, str]:
    if not payload or (isinstance(payload, dict) and payload.get("error")):
        return b"", ".wav"
    if isinstance(payload, dict):
        data_url = str(payload.get("audio") or "")
        mime = str(payload.get("mime") or "audio/webm")
    else:
        data_url = str(payload)
        mime = "audio/webm"
    suffix = ".webm" if "webm" in mime else ".wav"
    if "," in data_url:
        return base64.b64decode(data_url.split(",", 1)[1]), suffix
    return b"", suffix


def _play_tts_autoplay(audio_bytes: bytes | None, caption_text: str = "") -> None:
    """Play interviewer audio, then signal the mic to open when speech ends."""
    if not audio_bytes:
        return
    b64 = base64.b64encode(audio_bytes).decode()
    speech_seconds = _estimate_speech_seconds(caption_text) if caption_text else 8.0
    components.html(
        f"""
        <script>
        (function() {{
            const audio = new Audio("data:audio/mpeg;base64,{b64}");
            audio.playsInline = true;
            audio.play().catch(function() {{}});
            audio.addEventListener("ended", function() {{
                window.parent.postMessage({{
                    type: "interviewlab_start_mic",
                    silenceSeconds: {SILENCE_SUBMIT_SECONDS}
                }}, "*");
            }});
        }})();
        </script>
        """,
        height=0,
    )
    if caption_text:
        _set_live_caption("interviewer", caption_text, duration=speech_seconds)
    st.session_state["interview_phase"] = "interviewer_speaking"


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

    if st.session_state.pop("_end_interview_requested", False):
        _handle_end_interview(api_key)
        return

    if is_time_expired(state):
        _handle_time_expiry(api_key, state)
        return

    _render_meeting_room()
    _render_live_caption()


def _render_live_header() -> None:
    mode = st.session_state.get("interview_mode", "Behavioral")
    role = get_job_display_label(st.session_state)
    duration = st.session_state.get("interview_duration_minutes", 20)

    st.markdown(
        f"""
        <div class="interview-header">
            <div>
                <div class="interview-header-title">{mode} Interview · {role}</div>
                <div class="status-badge" style="margin-top:0.5rem">
                    <span class="status-dot"></span> Starting · English voice
                </div>
            </div>
            <div style="text-align:right">
                <div class="interview-timer">{duration:02d}:00</div>
                <div style="font-size:0.8rem;opacity:0.7;margin-top:0.25rem">
                    Interview starting…
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
        st.rerun(scope="app")
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
        st.rerun(scope="app")
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
                st.session_state["interview_phase"] = "interviewer_speaking"

        if result.get("action") == "complete":
            with st.spinner("Generating your evaluation…"):
                run_evaluation(client, state)

        apply_state_to_session(state, st.session_state)
        if result.get("action") != "complete":
            st.session_state["mic_turn_id"] = st.session_state.get("mic_turn_id", 0) + 1
        st.session_state.pop("last_mic_payload", None)
        st.rerun(scope="app")

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
            st.session_state["interview_phase"] = "interviewer_speaking"

        apply_state_to_session(state, st.session_state)
        st.session_state["_autoplay_tts"] = True
        st.rerun(scope="app")
    except Exception as exc:
        display_openai_error(exc)


def _handle_mic_payload(api_key: str, mic_payload: object) -> bool:
    """Process a microphone capture payload. Returns True if handled."""
    if not mic_payload or mic_payload == st.session_state.get("last_mic_payload"):
        return False

    st.session_state["last_mic_payload"] = mic_payload
    st.session_state["interview_phase"] = "listening"

    if isinstance(mic_payload, dict) and mic_payload.get("error") == "mic_denied":
        st.error("Microphone access is required. Allow the mic in your browser and refresh.")
        return True

    if isinstance(mic_payload, dict) and mic_payload.get("empty"):
        _process_answer(
            api_key,
            "I did not provide a verbal answer to this question.",
        )
        return True

    audio_bytes, suffix = _decode_mic_payload(mic_payload)
    _transcribe_and_submit(api_key, audio_bytes, suffix=suffix)
    return True


def _transcribe_and_submit(api_key: str, audio_bytes: bytes, *, suffix: str) -> None:
    if not audio_bytes:
        _process_answer(api_key, "I did not provide a verbal answer to this question.")
        return

    try:
        client = get_openai_client(api_key)
        with st.spinner("Transcribing your response…"):
            transcribed = transcribe_audio_bytes(client, audio_bytes, suffix=suffix)

        if not transcribed.strip():
            _process_answer(api_key, "I did not provide a verbal answer to this question.")
            return

        if not is_english_text(transcribed):
            st.warning(NON_ENGLISH_UI_MESSAGE)

        _set_live_caption("you", transcribed, duration=4.0)
        _process_answer(api_key, transcribed)
    except Exception as exc:
        _clear_live_caption()
        display_openai_error(exc)


def _render_voice_input(api_key: str) -> None:
    phase = st.session_state.get("interview_phase")
    if phase not in ("listening", "interviewer_speaking"):
        return

    if phase == "interviewer_speaking":
        st.markdown(
            '<p class="mic-active-hint">🎤 Interviewer speaking… your microphone opens automatically when they finish.</p>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<p class="mic-active-hint">🎙️ Your turn — microphone is live. '
            f'Speak naturally, click **Finish Answering**, or stay quiet for {SILENCE_SUBMIT_SECONDS}s to continue.</p>',
            unsafe_allow_html=True,
        )

    turn_id = st.session_state.get("mic_turn_id", 0)
    auto_start = st.session_state.pop("mic_auto_start", False)
    stop_now = st.session_state.pop("_stop_mic_now", False)

    mic_payload = render_auto_mic(
        auto_start=auto_start,
        stop_now=stop_now,
        silence_seconds=SILENCE_SUBMIT_SECONDS,
        key=f"auto_mic_{turn_id}",
    )

    if _handle_mic_payload(api_key, mic_payload):
        return

    if phase == "listening" and st.button(
        "Finish Answering →", type="primary", use_container_width=True
    ):
        st.session_state["_stop_mic_now"] = True
        st.rerun(scope="app")


def render_interview_view(api_key: str) -> None:
    session_started = st.session_state.get("interview_session_started", False)

    if st.session_state.pop("_auto_start_session", False) and not session_started:
        _handle_begin_session(api_key)
        return

    if session_started and st.session_state.pop("_autoplay_tts", False):
        audio = st.session_state.get("last_tts_audio")
        caption = st.session_state.pop("_autoplay_caption", "")
        if audio:
            _play_tts_autoplay(audio, caption)
            st.session_state["last_tts_audio"] = None
        elif caption:
            _set_live_caption("interviewer", caption, duration=_estimate_speech_seconds(caption))
            st.session_state["interview_phase"] = "listening"
            st.session_state["mic_auto_start"] = True

    if session_started:
        _timer_fragment(api_key)
        _render_voice_input(api_key)
        return

    _render_live_header()
    _render_meeting_room()
    st.markdown(
        '<p class="meeting-idle-hint">Starting your interview now…</p>',
        unsafe_allow_html=True,
    )
