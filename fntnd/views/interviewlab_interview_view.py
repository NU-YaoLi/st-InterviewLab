"""Active interview view — Realtime WebRTC English voice meeting."""

from __future__ import annotations

import html

import streamlit as st
import streamlit.components.v1 as components

from bknd.interviewlab_engine import (
    format_remaining_time,
    get_remaining_seconds,
    is_time_expired,
)
from bknd.interviewlab_evaluator import run_evaluation
from bknd.interviewlab_openai import get_openai_client
from bknd.interviewlab_realtime import finalize_realtime_interview, sync_transcript_to_state
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_realtime_component import render_realtime_interview
from fntnd.interviewlab_state import apply_state_to_session, get_job_display_label, state_from_session


def render_chat_history() -> None:
    """Full transcript for post-interview review."""
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


def _apply_realtime_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        return
    if payload == st.session_state.get("last_realtime_payload"):
        return
    st.session_state["last_realtime_payload"] = payload

    status = payload.get("status")
    # Ignore iframe remount reattach pings that don't change transcript length.
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
        # Prefer the latest completed interviewer turn as the sticky question caption.
        for msg in reversed(st.session_state["realtime_transcript"]):
            if msg.get("role") == "assistant" and msg.get("content"):
                st.session_state["live_caption_text"] = msg["content"]
                st.session_state["live_caption_speaker"] = "interviewer"
                break

    speaker = payload.get("active_speaker")
    if speaker == "you":
        st.session_state["active_speaker"] = "you"
        st.session_state["interview_phase"] = "listening"
    elif speaker == "interviewer":
        st.session_state["active_speaker"] = "interviewer"
        st.session_state["interview_phase"] = "interviewer_speaking"

    caption = payload.get("caption") or {}
    if isinstance(caption, dict) and caption.get("text"):
        # Only overwrite sticky caption for interviewer completed text.
        if caption.get("speaker") != "you":
            st.session_state["live_caption_text"] = caption.get("text")
            st.session_state["live_caption_speaker"] = "interviewer"

    event_type = payload.get("type")
    if event_type == "error":
        err = str(payload.get("error") or "realtime_error")
        # Keep a single sticky error; avoid stacking on every remount.
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
    elif payload.get("connected"):
        st.session_state.pop("_realtime_error", None)


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
        st.session_state.pop("_realtime_natural_complete", None)
        st.session_state.pop("_time_expired", None)
        st.rerun()
    except Exception as exc:
        apply_state_to_session(state, st.session_state)
        display_openai_error(exc)


def end_interview_and_show_results(api_key: str) -> None:
    """End Interview confirmed — disconnect Realtime on this run, evaluate next."""
    st.session_state["_disconnect_realtime"] = True
    st.session_state["_pending_finalize"] = "manual"
    # Evaluation happens in render_interview_view after the component sees disconnect.


def _handle_time_expiry(api_key: str) -> None:
    st.session_state["_disconnect_realtime"] = True
    st.session_state["_pending_finalize"] = "timer"


@st.fragment(run_every=2)
def _timer_fragment() -> None:
    if not st.session_state.get("interview_session_started"):
        return
    if not st.session_state.get("interview_active"):
        return

    state = state_from_session(st.session_state)
    _render_interview_header(state)

    if is_time_expired(state):
        st.session_state["_time_expired"] = True
        st.rerun()
        return

    _render_meeting_room()
    _render_live_caption()


def render_interview_view(api_key: str) -> None:
    from fntnd.interviewlab_state import reset_runtime_session

    # Second pass after disconnect was delivered to the WebRTC component.
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

    ephemeral = st.session_state.get("realtime_ephemeral_key")
    session_started = st.session_state.get("interview_session_started", False)

    if not session_started or not ephemeral:
        st.error("Live interview session is not ready. Please go back and start again.")
        if st.button("Return to setup"):
            reset_runtime_session()
            st.rerun()
        return

    _timer_fragment()

    disconnect = bool(st.session_state.get("_disconnect_realtime"))
    session_id = int(st.session_state.get("realtime_session_id") or 1)

    # Stable widget key for the whole interview — remounts must not mint a new key.
    payload = render_realtime_interview(
        ephemeral_key=str(ephemeral),
        session_id=session_id,
        disconnect=disconnect,
        key="realtime_live_session",
    )
    _apply_realtime_payload(payload)

    # After the component receives disconnect, finalize on the next full run.
    pending_finalize = st.session_state.pop("_pending_finalize", None)
    if pending_finalize:
        st.session_state["_do_finalize"] = pending_finalize
        st.rerun()
        return

    err = st.session_state.get("_realtime_error")
    if err:
        st.error(err)

    st.markdown(
        '<p class="mic-active-hint">🎙️ Live Realtime interview — speak naturally. '
        "Your interviewer will respond in real time. Use <strong>End Interview</strong> when finished.</p>",
        unsafe_allow_html=True,
    )
