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
    """Fallback only when browser cannot report real TTS duration."""
    words = len(text.split())
    return max(5.0, min(90.0, words * 0.55 + 1.5))


def _set_question_caption(text: str) -> None:
    st.session_state["live_caption_speaker"] = "interviewer"
    st.session_state["live_caption_text"] = text
    st.session_state["active_speaker"] = "interviewer"
    st.session_state["live_caption_expires_at"] = None
    st.session_state["current_question_text"] = text


def _clear_live_caption() -> None:
    st.session_state["live_caption_text"] = None
    st.session_state["live_caption_speaker"] = None
    st.session_state["live_caption_expires_at"] = None
    st.session_state["active_speaker"] = None


def _open_mic_turn() -> None:
    """Switch from interviewer speaking to candidate listening."""
    st.session_state["interview_phase"] = "listening"
    st.session_state["mic_auto_start"] = True
    st.session_state["active_speaker"] = "you"
    st.session_state.pop("_mic_open_after", None)
    if st.session_state.get("current_question_text"):
        st.session_state["live_caption_speaker"] = "interviewer"
        st.session_state["live_caption_text"] = st.session_state["current_question_text"]
        st.session_state["live_caption_expires_at"] = None


def _sync_mic_open_timer() -> bool:
    """Open mic from Python fallback timer. Returns True if phase changed."""
    open_after = st.session_state.get("_mic_open_after")
    if not open_after or time.time() < open_after:
        return False
    st.session_state.pop("_mic_open_after", None)
    if st.session_state.get("interview_phase") == "interviewer_speaking":
        _open_mic_turn()
        return True
    return False


def _timer_class(remaining_seconds: float) -> str:
    if remaining_seconds <= 60:
        return "interview-timer interview-timer-critical"
    if remaining_seconds <= 180:
        return "interview-timer interview-timer-warning"
    return "interview-timer"


def _paint_header_card() -> None:
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
            st.rerun()
    _paint_header_card()


def _inject_mic_control_script(*, action: str) -> None:
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
            if (run() || tries > 25) clearInterval(timer);
          }}, 200);
        }})();
        </script>
        """,
        height=0,
    )


def _play_tts_autoplay(audio_bytes: bytes | None, caption_text: str = "") -> None:
    """Play interviewer audio; open mic when audio ends (with duration fallback)."""
    if not audio_bytes:
        return
    b64 = base64.b64encode(audio_bytes).decode()
    fallback_seconds = _estimate_speech_seconds(caption_text) if caption_text else 12.0
    components.html(
        f"""
        <script>
        (function() {{
            function clickTtsDone() {{
              const doc = window.parent.document;
              const buttons = doc.querySelectorAll("button");
              for (let i = 0; i < buttons.length; i += 1) {{
                const label = (buttons[i].innerText || buttons[i].textContent || "").trim();
                if (label === "interviewlab_tts_done") {{
                  buttons[i].click();
                  return true;
                }}
              }}
              return false;
            }}
            function signalTtsDone() {{
              if (clickTtsDone()) return;
              let tries = 0;
              const timer = setInterval(function() {{
                tries += 1;
                if (clickTtsDone() || tries > 30) clearInterval(timer);
              }}, 150);
            }}
            const audio = new Audio("data:audio/mpeg;base64,{b64}");
            audio.playsInline = true;
            let signaled = false;
            function done() {{
              if (signaled) return;
              signaled = true;
              signalTtsDone();
            }}
            audio.addEventListener("ended", done);
            audio.addEventListener("error", done);
            audio.addEventListener("loadedmetadata", function() {{
              if (audio.duration && isFinite(audio.duration) && audio.duration > 0) {{
                setTimeout(done, (audio.duration + 0.6) * 1000);
              }}
            }});
            setTimeout(done, {int(fallback_seconds * 1000)});
            audio.play().catch(function() {{ done(); }});
        }})();
        </script>
        """,
        height=0,
    )
    if caption_text:
        _set_question_caption(caption_text)
    st.session_state["interview_phase"] = "interviewer_speaking"
    st.session_state["active_speaker"] = "interviewer"
    st.session_state["_mic_open_after"] = time.time() + fallback_seconds + 2.0


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


@st.fragment(run_every=2)
def _timer_fragment() -> None:
    """Lightweight timer refresh only — never runs heavy API work."""
    if st.session_state.get("interview_phase") == "processing":
        return
    if not st.session_state.get("interview_session_started"):
        return
    if not st.session_state.get("interview_active"):
        return

    # Mic-open fallback: request a full app rerun once, outside heavy work.
    if _sync_mic_open_timer():
        st.rerun()
        return

    state = state_from_session(st.session_state)
    _render_interview_header(state)
    if is_time_expired(state):
        st.session_state["_time_expired"] = True
        st.rerun()
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


def _handle_time_expiry(api_key: str) -> None:
    state = state_from_session(st.session_state)
    if not is_time_expired(state):
        return
    try:
        client = get_openai_client(api_key)
        force_close_interview(state, client)
        with st.spinner("Generating your evaluation…"):
            run_evaluation(client, state)
        _clear_live_caption()
        st.session_state.pop("current_question_text", None)
        st.session_state.pop("_time_expired", None)
        apply_state_to_session(state, st.session_state)
        st.rerun()
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
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)


def _queue_answer_processing(audio_bytes: bytes | None, *, suffix: str = ".wav") -> None:
    """Leave listening UI immediately; process on the next clean run."""
    st.session_state["interview_phase"] = "processing"
    st.session_state["_pending_audio_bytes"] = audio_bytes or b""
    st.session_state["_pending_audio_suffix"] = suffix
    st.session_state.pop("mic_auto_start", None)
    st.session_state.pop("_stop_mic_now", None)
    st.session_state.pop("_finish_after_stop", None)
    st.session_state.pop("_mic_open_after", None)
    st.rerun()


def _process_answer(api_key: str, user_answer: str) -> None:
    state = state_from_session(st.session_state)
    try:
        client = get_openai_client(api_key)
        _clear_live_caption()
        st.session_state.pop("current_question_text", None)

        result = process_user_response(state, client, user_answer)

        if PER_TURN_EVALUATION and result.get("user_answer") and state.responses:
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
            else:
                _set_question_caption(message)
                _open_mic_turn()
        else:
            st.session_state["interview_phase"] = "listening"

        if result.get("action") == "complete":
            run_evaluation(client, state)
            st.session_state["interview_phase"] = "complete"

        apply_state_to_session(state, st.session_state)
        if result.get("action") != "complete":
            st.session_state["mic_turn_id"] = st.session_state.get("mic_turn_id", 0) + 1
        st.session_state.pop("last_audio_payload_id", None)
        st.session_state.pop("_pending_audio_bytes", None)
        st.session_state.pop("_pending_audio_suffix", None)
        st.rerun()
    except Exception as exc:
        st.session_state["interview_phase"] = "listening"
        st.session_state.pop("_pending_audio_bytes", None)
        _clear_live_caption()
        display_openai_error(exc)


def _run_pending_answer_processing(api_key: str) -> None:
    """Transcribe + advance interview on a clean processing screen (no fragment churn)."""
    state = state_from_session(st.session_state)
    _render_interview_header(state)
    _render_meeting_room()
    st.markdown(
        '<p class="mic-active-hint">⏳ Processing your answer… preparing the next question.</p>',
        unsafe_allow_html=True,
    )

    audio_bytes = st.session_state.pop("_pending_audio_bytes", b"")
    suffix = st.session_state.pop("_pending_audio_suffix", ".wav")

    try:
        if not audio_bytes:
            with st.spinner("Moving to the next question…"):
                _process_answer(api_key, "I did not provide a verbal answer to this question.")
            return

        client = get_openai_client(api_key)
        with st.spinner("Transcribing your response…"):
            transcribed = transcribe_audio_bytes(client, audio_bytes, suffix=suffix)

        if not transcribed.strip():
            with st.spinner("Moving to the next question…"):
                _process_answer(api_key, "I did not provide a verbal answer to this question.")
            return

        if not is_english_text(transcribed):
            st.warning(NON_ENGLISH_UI_MESSAGE)

        with st.spinner("Interviewer is thinking…"):
            _process_answer(api_key, transcribed)
    except Exception as exc:
        st.session_state["interview_phase"] = "listening"
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
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)


def _render_voice_input(api_key: str) -> None:
    if _sync_mic_open_timer():
        st.rerun()
        return

    phase = st.session_state.get("interview_phase")
    if phase not in ("listening", "interviewer_speaking"):
        return

    if phase == "interviewer_speaking":
        st.markdown(
            '<p class="mic-active-hint">🎤 Interviewer speaking… your microphone opens automatically when they finish.</p>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="tts-done-marker"></div>', unsafe_allow_html=True)
        if st.button("interviewlab_tts_done", key="_tts_done_btn"):
            _open_mic_turn()
            st.rerun()
        return

    st.markdown(
        '<p class="mic-active-hint">🎙️ Your turn — speak your answer below, then click '
        "<strong>Finish Answering</strong> to continue.</p>",
        unsafe_allow_html=True,
    )

    turn_id = st.session_state.get("mic_turn_id", 0)
    auto_start = st.session_state.pop("mic_auto_start", False)

    if auto_start:
        st.session_state.pop("last_audio_payload_id", None)

    audio_value = st.audio_input(
        "Record your answer",
        key=f"interview_mic_{turn_id}",
        label_visibility="collapsed",
    )

    if auto_start:
        _inject_mic_control_script(action="start")

    if st.button("Finish Answering →", type="primary", use_container_width=True):
        if audio_value is not None:
            _queue_answer_processing(audio_value.getvalue(), suffix=".wav")
            return
        # Still recording / no clip yet — stop mic once, then process whatever we get.
        _inject_mic_control_script(action="stop")
        st.session_state["_finish_wait_ticks"] = 0
        st.session_state["interview_phase"] = "finishing"
        st.rerun()


def _render_finishing_capture(api_key: str) -> None:
    """Brief wait for Streamlit audio_input to flush after stop, then process."""
    state = state_from_session(st.session_state)
    _render_interview_header(state)
    _render_meeting_room()
    _render_live_caption()
    st.markdown(
        '<p class="mic-active-hint">⏳ Finishing your recording…</p>',
        unsafe_allow_html=True,
    )

    turn_id = st.session_state.get("mic_turn_id", 0)
    audio_value = st.audio_input(
        "Record your answer",
        key=f"interview_mic_{turn_id}",
        label_visibility="collapsed",
    )
    _inject_mic_control_script(action="stop")

    ticks = int(st.session_state.get("_finish_wait_ticks", 0))
    if audio_value is not None:
        st.session_state.pop("_finish_wait_ticks", None)
        _queue_answer_processing(audio_value.getvalue(), suffix=".wav")
        return

    if ticks >= 2:
        st.session_state.pop("_finish_wait_ticks", None)
        _queue_answer_processing(b"", suffix=".wav")
        return

    st.session_state["_finish_wait_ticks"] = ticks + 1
    time.sleep(0.35)
    st.rerun()


def render_interview_view(api_key: str) -> None:
    session_started = st.session_state.get("interview_session_started", False)

    if st.session_state.pop("_auto_start_session", False) and not session_started:
        _handle_begin_session(api_key)
        return

    if st.session_state.pop("_time_expired", False):
        _handle_time_expiry(api_key)
        return

    phase = st.session_state.get("interview_phase")
    if phase == "processing":
        _run_pending_answer_processing(api_key)
        return

    if phase == "finishing":
        _render_finishing_capture(api_key)
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
        _timer_fragment()
        _render_voice_input(api_key)
        return

    _render_live_header()
    _render_meeting_room()
    st.markdown(
        '<p class="meeting-idle-hint">Starting your interview now…</p>',
        unsafe_allow_html=True,
    )
