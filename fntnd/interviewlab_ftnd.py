"""
Top-level Streamlit UI for InterviewLab.

Modern main-page flow: setup → live interview → evaluation dashboard.
"""

from __future__ import annotations

import streamlit as st

from bknd.interviewlab_audio import synthesize_if_enabled
from bknd.interviewlab_engine import start_interview
from bknd.interviewlab_openai import get_openai_client
from fntnd.interviewlab_errors import (
    display_openai_error,
    queue_validation_error,
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
from fntnd.views.interviewlab_evaluation_view import render_evaluation_view
from fntnd.views.interviewlab_interview_view import render_chat_history, render_interview_view
from fntnd.views.interviewlab_landing_view import render_setup_view


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
        client = get_openai_client(api_key)
        state = state_from_session(st.session_state)
        state.ai_voice_enabled = True
        first_message = start_interview(state, client)
        state.last_tts_audio = synthesize_if_enabled(
            client, first_message, state.ai_voice_enabled
        )
        apply_state_to_session(state, st.session_state)
        st.session_state.pop("_generating_interview", None)
        st.session_state.pop("_generating_worker_started", None)
        st.session_state["_auto_start_session"] = True
        st.session_state["_autoplay_tts"] = True
        st.session_state["_autoplay_caption"] = first_message
        st.rerun()
    except Exception as exc:
        _abort_generating()
        display_openai_error(exc)


def main() -> None:
    init_session_state()
    inject_styles()

    interview_active = st.session_state.get("interview_active", False)
    interview_complete = st.session_state.get("interview_complete", False)

    if st.session_state.get("_generating_interview"):
        show_generating_dialog(
            lambda: _handle_start_interview(get_api_key_from_session())
        )
        return

    if interview_complete:
        render_evaluation_view()
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
        render_interview_view(api_key)
    else:
        show_queued_validation_error()
        render_setup_view()
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
