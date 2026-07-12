"""
Top-level Streamlit UI for InterviewLab.

Modern main-page flow: setup → live Realtime interview → evaluation dashboard.

View modules are imported lazily inside ``main()`` so Streamlit Cloud's
SourceFileLoader bootstrap does not fail on dotted package imports at module load.
"""

from __future__ import annotations

import sys

import streamlit as st

from bknd.interviewlab_realtime import create_realtime_client_secret, prepare_realtime_interview
from bknd.interviewlab_engine import begin_live_session
from fntnd.interviewlab_errors import (
    display_openai_error,
    queue_validation_error,
    show_end_interview_confirmation,
    show_ending_interview_dialog,
    show_generating_dialog,
    show_queued_validation_error,
    SERVICE_UNAVAILABLE_MESSAGE,
)
from fntnd.interviewlab_state import (
    apply_state_to_session,
    get_api_key_from_session,
    init_session_state,
    reset_runtime_session,
    state_from_session,
)
from fntnd.interviewlab_styles import inject_styles
from fntnd.interviewlab_transcript import render_chat_history


def _mod(name: str):
    """Return a bootstrapped module from sys.modules (Cloud-safe)."""
    mod = sys.modules.get(name)
    if mod is None:
        raise ImportError(f"Module not bootstrapped: {name}")
    return mod


def _abort_generating() -> None:
    st.session_state.pop("_generating_interview", None)
    st.session_state.pop("_generating_worker_started", None)


def _handle_start_interview(api_key: str) -> None:
    if not api_key:
        _abort_generating()
        queue_validation_error(SERVICE_UNAVAILABLE_MESSAGE)
        st.rerun()
        return
    if not st.session_state.get("job_description", "").strip():
        _abort_generating()
        queue_validation_error("Please enter **job details** before starting your mock interview.")
        st.rerun()
        return

    try:
        state = state_from_session(st.session_state)
        prepare_realtime_interview(state)
        ephemeral = create_realtime_client_secret(api_key, state)
        begin_live_session(state)
        apply_state_to_session(state, st.session_state)

        st.session_state["realtime_ephemeral_key"] = ephemeral
        st.session_state["realtime_session_id"] = (
            int(st.session_state.get("realtime_session_id") or 0) + 1
        )
        st.session_state["realtime_transcript"] = []
        st.session_state["interview_phase"] = "connecting"
        st.session_state["active_speaker"] = None
        st.session_state["live_caption_text"] = "Connecting to your interviewer…"
        st.session_state["live_caption_speaker"] = "interviewer"
        st.session_state["_disconnect_realtime"] = False
        st.session_state.pop("last_realtime_payload", None)

        st.session_state.pop("_generating_interview", None)
        st.session_state.pop("_generating_worker_started", None)
        st.rerun()
    except Exception as exc:
        _abort_generating()
        display_openai_error(exc)


def main() -> None:
    init_session_state()
    inject_styles()

    # Resolve views from sys.modules (set by interviewlab_main bootstrap).
    landing = _mod("fntnd.views.interviewlab_landing_view")
    interview = _mod("fntnd.views.interviewlab_interview_view")
    evaluation = _mod("fntnd.views.interviewlab_evaluation_view")

    interview_active = st.session_state.get("interview_active", False)
    interview_complete = st.session_state.get("interview_complete", False)

    if st.session_state.get("_generating_interview"):
        show_generating_dialog(
            lambda: _handle_start_interview(get_api_key_from_session())
        )
        return

    if interview_complete:
        evaluation.render_evaluation_view()
        st.divider()
        with st.expander("Full interview transcript"):
            render_chat_history()
    elif interview_active:
        api_key = get_api_key_from_session()
        if not api_key:
            queue_validation_error(SERVICE_UNAVAILABLE_MESSAGE)
            reset_runtime_session()
            st.rerun()
            return
        if st.session_state.get("_ending_interview"):
            show_ending_interview_dialog(
                lambda: interview.end_interview_and_show_results(api_key)
            )
            # Dialog owns this run — avoid re-rendering the live room underneath.
            return
        if st.session_state.pop("_show_end_interview_confirm", False):
            show_end_interview_confirmation()
            # Dialog owns this run — avoid re-rendering the live room underneath.
            return
        interview.render_interview_view(api_key)
    else:
        show_queued_validation_error()
        landing.render_setup_view()
        render_setup_footer()


@st.fragment
def _reset_controls_fragment() -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    st.button(
        "Reset",
        key="reset_setup",
        use_container_width=True,
        on_click=reset_runtime_session,
    )


def render_setup_footer() -> None:
    """Reset control isolated in a fragment so it does not rerun the full setup form."""
    if not st.session_state.get("interview_active") and not st.session_state.get(
        "interview_complete"
    ):
        _reset_controls_fragment()
