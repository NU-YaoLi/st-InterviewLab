"""Active interview view — Realtime WebRTC English voice meeting."""

from __future__ import annotations

import html
import time

import streamlit as st

from bknd.interviewlab_engine import (
    format_remaining_time,
    get_remaining_seconds,
    is_time_expired,
    start_interview_timer,
)
from bknd.interviewlab_evaluator import run_evaluation
from bknd.interviewlab_language import NON_ENGLISH_UI_MESSAGE, is_english_text
from bknd.interviewlab_openai import get_openai_client
from bknd.interviewlab_realtime import finalize_realtime_interview, sync_transcript_to_state
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_realtime_component import render_realtime_interview
from fntnd.interviewlab_state import apply_state_to_session, get_job_display_label, state_from_session
from interviewlab_config import REALTIME_SILENCE_DURATION_MS

_FINALIZE_TIMEOUT_SEC = 2.5


def _timer_class(remaining_seconds: float) -> str:
    if remaining_seconds <= 60:
        return "interview-timer interview-timer-critical"
    if remaining_seconds <= 180:
        return "interview-timer interview-timer-warning"
    return "interview-timer"


def _render_interview_header() -> None:
    mode = st.session_state.get("interview_mode", "Behavioral")
    role = get_job_display_label(st.session_state)
    connected = bool(st.session_state.get("interview_started_at"))
    status = "Live · English voice" if connected else "Connecting…"

    title_col, timer_col, end_col = st.columns([5.2, 2.2, 1.8], vertical_alignment="center")
    with title_col:
        st.markdown(
            f"""
            <div class="interview-header-title">{html.escape(str(mode))} Interview · {html.escape(str(role))}</div>
            <div class="status-badge" style="margin-top:0.5rem">
                <span class="status-dot"></span> {status}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with timer_col:
        _timer_display_fragment()
    with end_col:
        if st.button(
            "End Interview",
            type="secondary",
            key="end_interview_btn",
            use_container_width=True,
        ):
            st.session_state["_show_end_interview_confirm"] = True
            st.rerun()


@st.fragment(run_every=1)
def _timer_display_fragment() -> None:
    """Live countdown only — keeps the Realtime iframe outside this fragment."""
    if not st.session_state.get("interview_session_started"):
        return
    if not st.session_state.get("interview_active"):
        return

    state = state_from_session(st.session_state)
    if is_time_expired(state):
        st.session_state["_time_expired"] = True
        st.rerun()
        return

    timer_cls = _timer_class(get_remaining_seconds(state))
    timer_text = format_remaining_time(state)
    duration = st.session_state.get("interview_duration_minutes", 20)
    st.markdown(
        f"""
        <div class="interview-header-right" style="text-align:right">
            <div class="{timer_cls}">{timer_text}</div>
            <div style="font-size:0.8rem;opacity:0.75;margin-top:0.25rem;color:white">
                {duration} min session
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


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
    text = st.session_state.get("live_caption_text")
    speaker = st.session_state.get("live_caption_speaker") or "interviewer"
    if not text:
        return
    label = "Interviewer" if speaker == "interviewer" else "You"
    safe_text = html.escape(str(text))
    st.markdown(
        f"""
        <div class="live-caption-bar">
            <div class="live-caption-speaker">{label}</div>
            <div class="live-caption-text">{safe_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _maybe_note_non_english(transcript: list[dict[str, str]]) -> None:
    """Surface a one-time English reminder when a user turn looks non-English."""
    if st.session_state.get("_non_english_warned"):
        return
    for msg in reversed(transcript):
        if msg.get("role") != "user":
            continue
        content = (msg.get("content") or "").strip()
        if content and not is_english_text(content):
            st.session_state["_non_english_warned"] = True
            st.session_state["_realtime_notice"] = NON_ENGLISH_UI_MESSAGE
        break


def _apply_realtime_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        return
    if payload == st.session_state.get("last_realtime_payload"):
        return
    st.session_state["last_realtime_payload"] = payload

    status = payload.get("status")
    event_type = payload.get("type")

    if status == "reattached":
        transcript = payload.get("transcript")
        if isinstance(transcript, list):
            st.session_state["realtime_transcript"] = [
                {"role": m.get("role"), "content": m.get("content", "")}
                for m in transcript
                if isinstance(m, dict) and m.get("role") in ("assistant", "user")
            ]
        return

    transcript = payload.get("transcript")
    if isinstance(transcript, list):
        st.session_state["realtime_transcript"] = [
            {"role": m.get("role"), "content": m.get("content", "")}
            for m in transcript
            if isinstance(m, dict) and m.get("role") in ("assistant", "user")
        ]
        for msg in reversed(st.session_state["realtime_transcript"]):
            if msg.get("role") == "assistant" and msg.get("content"):
                st.session_state["live_caption_text"] = msg["content"]
                st.session_state["live_caption_speaker"] = "interviewer"
                break
        _maybe_note_non_english(st.session_state["realtime_transcript"])

    speaker = payload.get("active_speaker")
    if speaker == "you":
        st.session_state["active_speaker"] = "you"
        st.session_state["interview_phase"] = "listening"
    elif speaker == "interviewer":
        st.session_state["active_speaker"] = "interviewer"
        st.session_state["interview_phase"] = "interviewer_speaking"

    caption = payload.get("caption") or {}
    if isinstance(caption, dict) and caption.get("text"):
        if caption.get("speaker") != "you":
            st.session_state["live_caption_text"] = caption.get("text")
            st.session_state["live_caption_speaker"] = "interviewer"

    if event_type == "error":
        err = str(payload.get("error") or "realtime_error")
        if err == "mic_denied":
            st.session_state["_realtime_error"] = (
                "Microphone access is required. Allow the mic in your browser and refresh."
            )
        elif err in ("sdp_failed", "connect_failed", "missing_ephemeral_key"):
            st.session_state["_realtime_error"] = (
                "Live interview connection issue. Click End Interview, then start a new session."
            )
    elif event_type == "interview_complete" and not st.session_state.get("_disconnect_realtime"):
        st.session_state["_realtime_natural_complete"] = True
    elif event_type == "disconnected":
        st.session_state["_realtime_disconnected"] = True
    elif status == "connected" or (
        payload.get("connected") and st.session_state.get("interview_started_at") is None
    ):
        st.session_state.pop("_realtime_error", None)
        if st.session_state.get("interview_started_at") is None:
            state = state_from_session(st.session_state)
            start_interview_timer(state)
            apply_state_to_session(state, st.session_state)
            st.session_state["interview_phase"] = "live"
            st.session_state["_just_connected"] = True


def _finalize_and_evaluate(api_key: str, *, closing_note: str | None = None) -> None:
    state = state_from_session(st.session_state)
    transcript = list(st.session_state.get("realtime_transcript") or [])
    sync_transcript_to_state(state, transcript)
    if closing_note:
        state.chat_history.append({"role": "assistant", "content": closing_note})
    finalize_realtime_interview(state)

    try:
        client = get_openai_client(api_key)
        with st.spinner("Generating your evaluation…"):
            run_evaluation(client, state)
        apply_state_to_session(state, st.session_state)
        st.session_state["realtime_ephemeral_key"] = None
        st.session_state["_disconnect_realtime"] = False
        for key in (
            "_realtime_natural_complete",
            "_time_expired",
            "_pending_finalize",
            "_do_finalize",
            "_finalize_requested_at",
            "_realtime_disconnected",
            "_realtime_notice",
            "_non_english_warned",
        ):
            st.session_state.pop(key, None)
        st.rerun()
    except Exception as exc:
        apply_state_to_session(state, st.session_state)
        display_openai_error(exc)


def end_interview_and_show_results(api_key: str) -> None:
    """End Interview confirmed — disconnect Realtime, then evaluate with fallback."""
    del api_key  # used by caller for symmetry; finalize reads session key
    st.session_state["_disconnect_realtime"] = True
    st.session_state["_pending_finalize"] = "manual"
    st.session_state["_finalize_requested_at"] = time.time()


def _handle_time_expiry(api_key: str) -> None:
    del api_key
    st.session_state["_disconnect_realtime"] = True
    st.session_state["_pending_finalize"] = "timer"
    st.session_state["_finalize_requested_at"] = time.time()


def _should_finalize_now() -> str | None:
    """Return finalize reason when disconnect ack arrived or timeout elapsed."""
    pending = st.session_state.get("_pending_finalize")
    if not pending:
        return None
    if st.session_state.get("_realtime_disconnected"):
        return str(pending)
    started = st.session_state.get("_finalize_requested_at")
    if started is not None and (time.time() - float(started)) >= _FINALIZE_TIMEOUT_SEC:
        return str(pending)
    return None


def render_interview_view(api_key: str) -> None:
    from fntnd.interviewlab_state import reset_runtime_session

    pending = st.session_state.pop("_do_finalize", None)
    if pending == "manual":
        _finalize_and_evaluate(
            api_key,
            closing_note="Thank you — this mock interview has concluded.",
        )
        return
    if pending == "timer":
        _finalize_and_evaluate(
            api_key,
            closing_note="Time is up. Thank you — this mock interview has concluded.",
        )
        return
    if pending == "natural":
        _finalize_and_evaluate(api_key)
        return

    if st.session_state.pop("_time_expired", False):
        _handle_time_expiry(api_key)

    if st.session_state.pop("_realtime_natural_complete", False):
        st.session_state["_disconnect_realtime"] = True
        st.session_state["_pending_finalize"] = "natural"
        st.session_state["_finalize_requested_at"] = time.time()

    ephemeral = st.session_state.get("realtime_ephemeral_key")
    session_started = st.session_state.get("interview_session_started", False)

    if not session_started or not ephemeral:
        st.error("Live interview session is not ready. Please go back and start again.")
        if st.button("Return to setup"):
            reset_runtime_session()
            st.rerun()
        return

    _render_interview_header()
    _render_meeting_room()
    _render_live_caption()

    disconnect = bool(st.session_state.get("_disconnect_realtime"))
    session_id = int(st.session_state.get("realtime_session_id") or 1)
    silence_secs = max(1, int(round(REALTIME_SILENCE_DURATION_MS / 1000)))

    # Compact audio bridge — status/captions live in the Python meeting UI above.
    payload = render_realtime_interview(
        ephemeral_key=str(ephemeral),
        session_id=session_id,
        disconnect=disconnect,
        silence_seconds=silence_secs,
        key="realtime_live_session",
    )
    _apply_realtime_payload(payload)

    reason = _should_finalize_now()
    if reason:
        st.session_state.pop("_pending_finalize", None)
        st.session_state["_do_finalize"] = reason
        st.rerun()
        return

    err = st.session_state.get("_realtime_error")
    if err:
        st.error(err)

    notice = st.session_state.get("_realtime_notice")
    if notice:
        st.warning(notice)

    st.markdown(
        f'<p class="mic-active-hint">Live Realtime interview — speak naturally. '
        f"<strong>Tip:</strong> stay quiet for <strong>{silence_secs} seconds</strong> when you "
        "finish an answer to continue to the next question. "
        "Use <strong>End Interview</strong> when you want to stop the session.</p>",
        unsafe_allow_html=True,
    )
