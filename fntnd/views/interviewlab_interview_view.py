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


def _set_question_caption(text: str) -> None:
    """Keep the current interviewer question visible until the answer is submitted."""
    st.session_state["live_caption_speaker"] = "interviewer"
    st.session_state["live_caption_text"] = text
    st.session_state["active_speaker"] = "interviewer"
    st.session_state["live_caption_expires_at"] = None
    st.session_state["current_question_text"] = text


def _set_you_caption(text: str, *, duration: float = 4.0) -> None:
    st.session_state["live_caption_speaker"] = "you"
    st.session_state["live_caption_text"] = text
    st.session_state["active_speaker"] = "you"
    st.session_state["live_caption_expires_at"] = time.time() + duration


def _clear_live_caption() -> None:
    st.session_state["live_caption_text"] = None
    st.session_state["live_caption_speaker"] = None
    st.session_state["live_caption_expires_at"] = None
    st.session_state["active_speaker"] = None


def _open_mic_turn() -> None:
    """Switch from interviewer speaking to candidate listening and show the mic."""
    st.session_state["interview_phase"] = "listening"
    st.session_state["mic_auto_start"] = True
    st.session_state["active_speaker"] = "you"
    st.session_state.pop("_mic_open_after", None)
    # Keep the interviewer question caption visible while the candidate answers.
    if st.session_state.get("current_question_text"):
        st.session_state["live_caption_speaker"] = "interviewer"
        st.session_state["live_caption_text"] = st.session_state["current_question_text"]
        st.session_state["live_caption_expires_at"] = None


def _sync_interview_phase_timers() -> bool:
    """Open the mic when TTS finishes. Returns True if an app-level rerun is needed."""
    open_after = st.session_state.get("_mic_open_after")
    if open_after and time.time() >= open_after:
        if st.session_state.get("interview_phase") == "interviewer_speaking":
            _open_mic_turn()
            return True
        st.session_state.pop("_mic_open_after", None)
    return False


def _timer_class(remaining_seconds: float) -> str:
    if remaining_seconds <= 60:
        return "interview-timer interview-timer-critical"
    if remaining_seconds <= 180:
        return "interview-timer interview-timer-warning"
    return "interview-timer"


def _paint_header_card() -> None:
    """Apply the solid purple background to the header row that contains End Interview."""
    components.html(
        """
        <script>
        (function() {
          const doc = window.parent.document;
          function paint() {
            const buttons = doc.querySelectorAll('button');
            let endBtn = null;
            buttons.forEach((btn) => {
              const label = (btn.innerText || btn.textContent || "").trim();
              if (label === "End Interview") endBtn = btn;
            });
            if (!endBtn) return false;
            const row = endBtn.closest('[data-testid="stHorizontalBlock"]');
            if (!row) return false;
            row.classList.add("interview-header-row");
            return true;
          }
          let tries = 0;
          const timer = setInterval(function() {
            tries += 1;
            if (paint() || tries > 20) clearInterval(timer);
          }, 100);
        })();
        </script>
        """,
        height=0,
    )


def _render_interview_header(state: object) -> None:
    """Full-width purple title card with End Interview on the right."""
    timer_cls = _timer_class(get_remaining_seconds(state))
    mode = st.session_state.get("interview_mode", "Behavioral")
    role = get_job_display_label(st.session_state)
    duration = st.session_state.get("interview_duration_minutes", 20)
    timer_text = format_remaining_time(state)

    title_col, timer_col, end_col = st.columns([5.2, 2.2, 1.8], vertical_alignment="center")
    with title_col:
        st.markdown(
            f"""
            <div class="interview-header-title">{html.escape(str(mode))} Interview · {html.escape(str(role))}</div>
            <div class="status-badge" style="margin-top:0.5rem">
                <span class="status-dot"></span> Live · English voice
            </div>
            """,
            unsafe_allow_html=True,
        )
    with timer_col:
        st.markdown(
            f"""
            <div class="interview-header-right">
                <div class="{timer_cls}">{timer_text}</div>
                <div style="font-size:0.8rem;opacity:0.75;margin-top:0.25rem">
                    {duration} min session
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with end_col:
        if st.button("End Interview", type="secondary", key="end_interview_btn", use_container_width=True):
            st.session_state["_show_end_interview_confirm"] = True
            st.rerun(scope="app")
    _paint_header_card()


def _inject_mic_control_script(*, action: str) -> None:
    """Auto-start or stop Streamlit's native audio recorder."""
    components.html(
        f"""
        <script>
        (function() {{
          function micButton() {{
            const doc = window.parent.document;
            const widgets = doc.querySelectorAll('[data-testid="stAudioInput"]');
            const widget = widgets[widgets.length - 1];
            if (!widget) return null;
            return widget.querySelector("button");
          }}
          function run() {{
            const btn = micButton();
            if (!btn) return false;
            const label = (btn.getAttribute("aria-label") || btn.textContent || "").toLowerCase();
            if ("{action}" === "start") {{
              if (label.includes("stop") || label.includes("recording")) return true;
              btn.click();
              return true;
            }}
            if (label.includes("stop") || label.includes("recording")) {{
              btn.click();
              return true;
            }}
            return false;
          }}
          let tries = 0;
          const timer = setInterval(function() {{
            tries += 1;
            if (run() || tries > 40) clearInterval(timer);
          }}, 200);
        }})();
        </script>
        """,
        height=0,
    )


def _play_tts_autoplay(audio_bytes: bytes | None, caption_text: str = "") -> None:
    """Play interviewer audio and schedule the candidate mic to open when speech ends."""
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
        }})();
        </script>
        """,
        height=0,
    )
    if caption_text:
        _set_question_caption(caption_text)
    st.session_state["interview_phase"] = "interviewer_speaking"
    st.session_state["active_speaker"] = "interviewer"
    st.session_state["_mic_open_after"] = time.time() + speech_seconds


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
    text = st.session_state.get("live_caption_text") or st.session_state.get("current_question_text")
    speaker = st.session_state.get("live_caption_speaker") or "interviewer"
    if not text:
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


@st.fragment(run_every=1)
def _timer_fragment(api_key: str) -> None:
    """Auto-refresh timer; trigger full rerun when mic should open."""
    if _sync_interview_phase_timers():
        st.rerun(scope="app")
        return

    if not st.session_state.get("interview_session_started"):
        return

    state = state_from_session(st.session_state)
    if not st.session_state.get("interview_active"):
        return

    _render_interview_header(state)

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
            <div class="interview-header-left">
                <div class="interview-header-title">{mode} Interview · {role}</div>
                <div class="status-badge" style="margin-top:0.5rem">
                    <span class="status-dot"></span> Starting · English voice
                </div>
            </div>
            <div class="interview-header-right">
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
        st.session_state.pop("current_question_text", None)
        apply_state_to_session(state, st.session_state)
        st.rerun(scope="app")
    except Exception as exc:
        display_openai_error(exc)


def end_interview_and_show_results(api_key: str) -> None:
    state = state_from_session(st.session_state)
    try:
        client = get_openai_client(api_key)
        with st.spinner("Ending interview…"):
            end_interview_manually(state, client)
            run_evaluation(client, state)
        _clear_live_caption()
        st.session_state.pop("current_question_text", None)
        apply_state_to_session(state, st.session_state)
        st.rerun(scope="app")
    except Exception as exc:
        display_openai_error(exc)


def _process_answer(api_key: str, user_answer: str) -> None:
    state = state_from_session(st.session_state)
    try:
        client = get_openai_client(api_key)
        # Clear previous question only once the answer is being processed.
        _clear_live_caption()
        st.session_state.pop("current_question_text", None)

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
        st.session_state.pop("last_audio_payload_id", None)
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
            _set_question_caption(last_message)

        apply_state_to_session(state, st.session_state)
        st.session_state["_autoplay_tts"] = True
        st.rerun(scope="app")
    except Exception as exc:
        display_openai_error(exc)


def _render_voice_input(api_key: str) -> None:
    if _sync_interview_phase_timers():
        st.rerun(scope="app")
        return

    phase = st.session_state.get("interview_phase")
    if phase not in ("listening", "interviewer_speaking"):
        return

    if phase == "interviewer_speaking":
        st.markdown(
            '<p class="mic-active-hint">🎤 Interviewer speaking… your microphone opens automatically when they finish.</p>',
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<p class="mic-active-hint">🎙️ Your turn — speak your answer below, then click '
        "<strong>Finish Answering</strong> to continue.</p>",
        unsafe_allow_html=True,
    )

    turn_id = st.session_state.get("mic_turn_id", 0)
    auto_start = st.session_state.pop("mic_auto_start", False)
    stop_now = st.session_state.pop("_stop_mic_now", False)

    if auto_start:
        st.session_state.pop("last_audio_payload_id", None)

    audio_value = st.audio_input(
        "Record your answer",
        key=f"interview_mic_{turn_id}",
        label_visibility="collapsed",
    )

    if auto_start:
        _inject_mic_control_script(action="start")
    if stop_now:
        _inject_mic_control_script(action="stop")

    if st.session_state.pop("_finish_after_stop", False):
        if audio_value is not None:
            payload_id = f"{turn_id}:{getattr(audio_value, 'size', len(audio_value.getvalue()))}"
            if payload_id != st.session_state.get("last_audio_payload_id"):
                st.session_state["last_audio_payload_id"] = payload_id
                _transcribe_and_submit(api_key, audio_value.getvalue(), suffix=".wav")
                return
        _process_answer(api_key, "I did not provide a verbal answer to this question.")
        return

    if st.button("Finish Answering →", type="primary", use_container_width=True):
        if audio_value is not None:
            payload_id = f"{turn_id}:{getattr(audio_value, 'size', len(audio_value.getvalue()))}"
            st.session_state["last_audio_payload_id"] = payload_id
            _transcribe_and_submit(api_key, audio_value.getvalue(), suffix=".wav")
            return
        # Stop an in-progress recording, then submit on the next rerun.
        st.session_state["_stop_mic_now"] = True
        st.session_state["_finish_after_stop"] = True
        st.rerun(scope="app")


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

        _set_you_caption(transcribed, duration=4.0)
        _process_answer(api_key, transcribed)
    except Exception as exc:
        _clear_live_caption()
        display_openai_error(exc)


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
            _set_question_caption(caption)
            _open_mic_turn()

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
