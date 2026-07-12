"""Active interview view — Realtime WebRTC English voice meeting."""

from __future__ import annotations

import html

import streamlit as st

from bknd.interviewlab_engine import (
    format_remaining_time,
    get_remaining_seconds,
    is_time_expired,
    start_interview_timer,
)
from bknd.interviewlab_evaluator import run_evaluation
from bknd.interviewlab_completion import looks_like_interview_end
from bknd.interviewlab_language import NON_ENGLISH_UI_MESSAGE, is_english_text
from bknd.interviewlab_openai import get_openai_client
from bknd.interviewlab_realtime import (
    finalize_realtime_interview,
    sync_transcript_to_state,
)
from bknd.interviewlab_security import SECURITY_UI_TERMINATED, SECURITY_UI_WARNING
from fntnd.interviewlab_errors import display_openai_error
from fntnd.interviewlab_realtime_component import render_realtime_interview
from fntnd.interviewlab_state import apply_state_to_session, get_job_display_label, state_from_session
from interviewlab_config import REALTIME_SILENCE_DURATION_MS, SECURITY_MAX_CONSECUTIVE_STRIKES


def _normalize_transcript_turns(transcript: list) -> list[dict]:
    """Keep role/content plus security flags for evaluation filtering."""
    cleaned: list[dict] = []
    for msg in transcript:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role not in ("assistant", "user"):
            continue
        turn: dict = {"role": role, "content": msg.get("content", "")}
        if msg.get("security_blocked") or msg.get("security_flag"):
            turn["security_blocked"] = True
            turn["security_flag"] = True
        cleaned.append(turn)
    return cleaned


def _timer_class(remaining_seconds: float) -> str:
    if remaining_seconds <= 60:
        return "interview-timer interview-timer-critical"
    if remaining_seconds <= 180:
        return "interview-timer interview-timer-warning"
    return "interview-timer"


def _render_interview_header() -> None:
    mode = st.session_state.get("interview_mode", "Behavioral")
    role = get_job_display_label(st.session_state)
    # Timer starts only after the WebRTC bridge emits connected — keep header in sync.
    connected = st.session_state.get("interview_started_at") is not None
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


def _render_meeting_room_into(slot) -> None:
    """Paint participant tiles into a reserved layout slot (after payload apply)."""
    active = st.session_state.get("active_speaker")
    interviewer_cls = "participant-tile speaking" if active == "interviewer" else "participant-tile"
    you_cls = "participant-tile speaking" if active == "you" else "participant-tile"
    interviewer_status = "Speaking…" if active == "interviewer" else "Interviewer"
    you_status = "Speaking…" if active == "you" else "You"

    slot.markdown(
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


def _sync_interviewer_caption_from_transcript() -> None:
    """Keep sticky caption on the latest interviewer turn in the transcript."""
    for msg in reversed(st.session_state.get("realtime_transcript") or []):
        if msg.get("role") == "assistant" and (msg.get("content") or "").strip():
            st.session_state["live_caption_text"] = msg["content"]
            st.session_state["live_caption_speaker"] = "interviewer"
            return


def _interviewer_caption_text() -> str:
    """Return the sticky interviewer caption, never the connecting placeholder."""
    text = (st.session_state.get("live_caption_text") or "").strip()
    if text.lower().startswith("connecting to your interviewer"):
        _sync_interviewer_caption_from_transcript()
        text = (st.session_state.get("live_caption_text") or "").strip()
        if text.lower().startswith("connecting to your interviewer"):
            return ""
    return text


def _render_live_caption_into(slot) -> None:
    """Paint interviewer-only caption into a reserved layout slot."""
    text = _interviewer_caption_text()
    if not text:
        slot.empty()
        return
    safe_text = html.escape(str(text))
    slot.markdown(
        f"""
        <div class="live-caption-bar">
            <div class="live-caption-speaker">Interviewer</div>
            <div class="live-caption-text">{safe_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_session_tip(silence_secs: int) -> None:
    st.markdown(
        f'<p class="mic-active-hint">Live Realtime interview — speak naturally.<br>'
        f"<strong>Tip:</strong> stay quiet for <strong>{silence_secs} seconds</strong> when you "
        "finish an answer to continue to the next question. "
        "Use <strong>End Interview</strong> when you want to stop the session.</p>",
        unsafe_allow_html=True,
    )


def _maybe_note_non_english(transcript: list[dict[str, str]]) -> None:
    """Surface a one-time English reminder when a user turn looks non-English."""
    if st.session_state.get("_non_english_warned"):
        return
    for msg in reversed(transcript):
        if msg.get("role") != "user":
            continue
        if msg.get("security_blocked") or msg.get("security_flag"):
            break
        content = (msg.get("content") or "").strip()
        if content and not is_english_text(content):
            st.session_state["_non_english_warned"] = True
            st.session_state["_realtime_notice"] = NON_ENGLISH_UI_MESSAGE
        break


def _maybe_mark_natural_complete_from_transcript(transcript: list[dict]) -> None:
    """Python-side auto-end when interviewer closing speech is detected."""
    if st.session_state.get("_disconnect_realtime") or st.session_state.get("_ending_interview"):
        return
    if st.session_state.get("_realtime_natural_complete"):
        return
    for msg in reversed(transcript):
        if msg.get("role") != "assistant":
            continue
        content = (msg.get("content") or "").strip()
        if content and looks_like_interview_end(content):
            st.session_state["_realtime_natural_complete"] = True
        break


def _refresh_ephemeral_for_reconnect(api_key: str) -> bool:
    """
    Mint a fresh ephemeral key and bump session_id so the WebRTC bridge reconnects.

    Returns True on success. Preserves transcript / interview progress.
    """
    from fntnd.interviewlab_ftnd import mint_and_store_ephemeral_key

    try:
        state = state_from_session(st.session_state)
        # Sync progress so reminted instructions can continue mid-interview.
        transcript = list(st.session_state.get("realtime_transcript") or [])
        sync_transcript_to_state(state, transcript)
        apply_state_to_session(state, st.session_state)
        # Always remint — reconnect needs a secret that can open a new WebRTC call.
        mint_and_store_ephemeral_key(api_key, state)
        st.session_state["_disconnect_realtime"] = False
        st.session_state.pop("_realtime_error", None)
        st.session_state.pop("_realtime_connect_failed", None)
        st.session_state.pop("_realtime_disconnected", None)
        st.session_state.pop("last_realtime_payload", None)
        st.session_state["interview_phase"] = "connecting"
        st.session_state["active_speaker"] = None
        st.session_state["live_caption_text"] = "Reconnecting to your interviewer…"
        st.session_state["live_caption_speaker"] = "interviewer"
        return True
    except Exception as exc:
        display_openai_error(exc)
        return False


def _apply_realtime_payload(payload: object) -> None:
    """Apply bridge payload into session state (caption + speaker + transcript)."""
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
            st.session_state["realtime_transcript"] = _normalize_transcript_turns(transcript)
            _sync_interviewer_caption_from_transcript()
            _maybe_mark_natural_complete_from_transcript(
                st.session_state["realtime_transcript"]
            )
        return

    transcript = payload.get("transcript")
    if isinstance(transcript, list):
        st.session_state["realtime_transcript"] = _normalize_transcript_turns(transcript)
        _sync_interviewer_caption_from_transcript()
        _maybe_note_non_english(st.session_state["realtime_transcript"])
        _maybe_mark_natural_complete_from_transcript(st.session_state["realtime_transcript"])

    if event_type == "security_warning":
        strikes = int(payload.get("security_strikes") or 0)
        st.session_state["security_consecutive_strikes"] = strikes
        st.session_state["_security_notice"] = SECURITY_UI_WARNING
        return

    if event_type == "language_warning":
        st.session_state["_non_english_warned"] = True
        st.session_state["_realtime_notice"] = NON_ENGLISH_UI_MESSAGE
        return

    if event_type == "security_terminated":
        strikes = int(
            payload.get("security_strikes")
            or st.session_state.get("security_consecutive_strikes")
            or SECURITY_MAX_CONSECUTIVE_STRIKES
        )
        st.session_state["security_consecutive_strikes"] = strikes
        st.session_state["security_terminated"] = True
        st.session_state["_security_notice"] = SECURITY_UI_TERMINATED
        st.session_state["_security_finalize"] = True
        st.session_state["_disconnect_realtime"] = True
        return

    speaker = payload.get("active_speaker")
    if speaker == "you":
        st.session_state["active_speaker"] = "you"
        st.session_state["interview_phase"] = "listening"
    elif speaker == "interviewer":
        st.session_state["active_speaker"] = "interviewer"
        st.session_state["interview_phase"] = "interviewer_speaking"
    elif speaker == "none":
        st.session_state["active_speaker"] = None
        st.session_state["interview_phase"] = "waiting"

    caption = payload.get("caption") or {}
    if isinstance(caption, dict) and caption.get("speaker") != "you":
        text = (caption.get("text") or "").strip()
        # Ignore empty / connecting placeholders once we have a real question.
        if text and not text.lower().startswith("connecting to your interviewer"):
            st.session_state["live_caption_text"] = text
            st.session_state["live_caption_speaker"] = "interviewer"
            if looks_like_interview_end(text):
                st.session_state["_realtime_natural_complete"] = True
        elif not text:
            _sync_interviewer_caption_from_transcript()

    if event_type == "error":
        # Intentional teardown / wrap-up — never surface as a cold-start failure.
        if (
            st.session_state.get("_disconnect_realtime")
            or st.session_state.get("_ending_interview")
            or st.session_state.get("interview_complete")
        ):
            return
        err = str(payload.get("error") or "realtime_error")
        already_live = st.session_state.get("interview_started_at") is not None
        st.session_state["_realtime_connect_failed"] = True
        if err == "mic_denied":
            st.session_state["_realtime_error"] = (
                "Microphone access is required. Allow the mic in your browser, then click "
                "Retry connection."
            )
        elif err in (
            "sdp_failed",
            "connect_failed",
            "connect_timeout",
            "missing_ephemeral_key",
        ):
            if already_live:
                st.session_state["_realtime_error"] = (
                    "Live interview connection lost. Click Retry connection to continue, "
                    "or End Interview to save your progress."
                )
                st.session_state["_realtime_disconnected"] = True
            else:
                st.session_state["_realtime_error"] = (
                    "Could not connect to the live interviewer. Click Retry connection, "
                    "or End Interview to leave."
                )
        else:
            st.session_state["_realtime_error"] = (
                "Live interview hit a connection problem. Click Retry connection or End Interview."
            )
    elif event_type == "interview_complete" and not st.session_state.get("_disconnect_realtime"):
        st.session_state["_realtime_natural_complete"] = True
    elif event_type == "disconnected":
        # Intentional End / finalize — ignore.
        if (
            st.session_state.get("_disconnect_realtime")
            or st.session_state.get("_ending_interview")
            or st.session_state.get("interview_complete")
            or st.session_state.get("_security_finalize")
        ):
            return
        # Unexpected mid-session drop — surface recovery UI.
        if st.session_state.get("interview_started_at") is not None:
            st.session_state["_realtime_disconnected"] = True
            st.session_state["_realtime_error"] = (
                "Live interview connection dropped. Click Retry connection to continue, "
                "or End Interview to save your progress."
            )
    elif status == "connected" or (
        payload.get("connected") and st.session_state.get("interview_started_at") is None
    ):
        st.session_state.pop("_realtime_error", None)
        st.session_state.pop("_realtime_connect_failed", None)
        st.session_state.pop("_realtime_disconnected", None)
        # Drop the setup placeholder so the first real interviewer caption can show.
        connecting = (st.session_state.get("live_caption_text") or "").strip().lower()
        if connecting.startswith("connecting to your interviewer") or connecting.startswith(
            "reconnecting to your interviewer"
        ):
            st.session_state["live_caption_text"] = "Interviewer is speaking…"
            st.session_state["live_caption_speaker"] = "interviewer"
        if st.session_state.get("interview_started_at") is None:
            state = state_from_session(st.session_state)
            start_interview_timer(state)
            apply_state_to_session(state, st.session_state)
            st.session_state["interview_phase"] = "live"
            st.session_state["_just_connected"] = True
        else:
            # Successful reconnect after a drop — keep original timer.
            st.session_state["interview_phase"] = "live"
            st.session_state["_just_connected"] = True


def _clear_finalize_flags() -> None:
    for key in (
        "_realtime_natural_complete",
        "_time_expired",
        "_pending_finalize",
        "_do_finalize",
        "_finalize_requested_at",
        "_realtime_disconnected",
        "_realtime_notice",
        "_non_english_warned",
        "_realtime_connect_failed",
        "_show_end_interview_confirm",
        "_ending_interview",
        "_ending_worker_started",
        "_security_finalize",
        "_security_notice",
        "_retry_realtime_connect",
    ):
        st.session_state.pop(key, None)


def _finalize_and_evaluate(api_key: str, *, closing_note: str | None = None) -> None:
    """Score from the current transcript and jump to results — do not wait on WebRTC."""
    state = state_from_session(st.session_state)
    transcript = list(st.session_state.get("realtime_transcript") or [])
    sync_transcript_to_state(state, transcript)
    if closing_note:
        state.chat_history.append({"role": "assistant", "content": closing_note})
    finalize_realtime_interview(state)

    security_terminated = bool(st.session_state.get("security_terminated"))
    security_strikes = int(st.session_state.get("security_consecutive_strikes") or 0)

    try:
        # Empty sessions return a local zero score (no LLM call).
        # Security-terminated sessions return a locked zero score (no LLM call).
        client = get_openai_client(api_key)
        run_evaluation(
            client,
            state,
            security_terminated=security_terminated,
            security_strikes=security_strikes,
        )
        apply_state_to_session(state, st.session_state)
        st.session_state["realtime_ephemeral_key"] = None
        st.session_state["realtime_ephemeral_expires_at"] = None
        st.session_state["_disconnect_realtime"] = True
        _clear_finalize_flags()
    except Exception as exc:
        apply_state_to_session(state, st.session_state)
        display_openai_error(exc)


def end_interview_and_show_results(api_key: str) -> None:
    """End Interview confirmed — evaluate immediately; WebRTC cleanup is best-effort."""
    _finalize_and_evaluate(
        api_key,
        closing_note="Thank you — this mock interview has concluded.",
    )


def _handle_time_expiry(api_key: str) -> None:
    st.session_state["_disconnect_realtime"] = True
    _finalize_and_evaluate(
        api_key,
        closing_note="Time is up. Thank you — this mock interview has concluded.",
    )


def _render_connection_recovery(api_key: str) -> None:
    """Retry / End controls when connect fails or the live link drops."""
    err = st.session_state.get("_realtime_error")
    if err:
        st.error(err)
    disconnected = bool(st.session_state.get("_realtime_disconnected"))
    failed = bool(st.session_state.get("_realtime_connect_failed"))
    if not (disconnected or failed or err):
        return

    retry_col, end_col = st.columns(2)
    with retry_col:
        if st.button("Retry connection", type="primary", use_container_width=True):
            if _refresh_ephemeral_for_reconnect(api_key):
                st.rerun()
    with end_col:
        if st.button("End Interview", type="secondary", use_container_width=True, key="end_after_disconnect"):
            st.session_state["_show_end_interview_confirm"] = True
            st.rerun()


def render_interview_view(api_key: str) -> None:
    from fntnd.interviewlab_state import reset_runtime_session

    if st.session_state.pop("_time_expired", False):
        _handle_time_expiry(api_key)
        st.rerun()
        return

    if st.session_state.pop("_security_finalize", False):
        st.session_state["_disconnect_realtime"] = True
        _finalize_and_evaluate(
            api_key,
            closing_note=SECURITY_UI_TERMINATED,
        )
        st.rerun()
        return

    if st.session_state.pop("_realtime_natural_complete", False):
        st.session_state["_disconnect_realtime"] = True
        _finalize_and_evaluate(api_key)
        st.rerun()
        return

    # Interview already finalized (e.g. from End dialog) — leave this view.
    if st.session_state.get("interview_complete"):
        st.rerun()
        return

    ephemeral = st.session_state.get("realtime_ephemeral_key")
    session_started = st.session_state.get("interview_session_started", False)

    if not session_started or not ephemeral:
        st.error("Live interview session is not ready. Please go back and start again.")
        if st.button("Return to setup"):
            reset_runtime_session()
            st.rerun()
        return

    silence_secs = max(1, int(round(REALTIME_SILENCE_DURATION_MS / 1000)))
    disconnect = bool(st.session_state.get("_disconnect_realtime"))
    session_id = int(st.session_state.get("realtime_session_id") or 1)
    # After a failed connect / unexpected drop, do not auto-restart WebRTC every rerun.
    # Retry connection remints a key and clears these flags.
    hold_connect = (
        not disconnect
        and (
            st.session_state.get("_realtime_connect_failed")
            or st.session_state.get("_realtime_disconnected")
        )
    )

    _render_interview_header()
    _render_session_tip(silence_secs)
    # Reserve layout slots, then fill after payload so speaking tiles stay in sync.
    meeting_slot = st.empty()
    caption_slot = st.empty()

    payload = render_realtime_interview(
        ephemeral_key="" if hold_connect else str(ephemeral),
        session_id=session_id,
        disconnect=disconnect,
        silence_seconds=silence_secs,
        key="realtime_live_session",
    )
    _apply_realtime_payload(payload)
    _render_meeting_room_into(meeting_slot)
    _render_live_caption_into(caption_slot)

    if st.session_state.pop("_just_connected", False):
        st.rerun()
        return

    if st.session_state.pop("_security_finalize", False):
        st.session_state["_disconnect_realtime"] = True
        _finalize_and_evaluate(
            api_key,
            closing_note=SECURITY_UI_TERMINATED,
        )
        st.rerun()
        return

    # Natural completion signaled by the bridge after the last interviewer turn.
    if st.session_state.pop("_realtime_natural_complete", False):
        st.session_state["_disconnect_realtime"] = True
        _finalize_and_evaluate(api_key)
        st.rerun()
        return

    _render_connection_recovery(api_key)

    security_notice = st.session_state.get("_security_notice")
    if security_notice:
        st.error(security_notice)
    else:
        notice = st.session_state.get("_realtime_notice")
        if notice:
            st.warning(notice)
