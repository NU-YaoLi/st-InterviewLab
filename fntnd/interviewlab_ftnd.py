"""
Top-level Streamlit UI for InterviewLab.

Modern main-page flow: setup → live interview → evaluation dashboard.
"""

from __future__ import annotations

import streamlit as st

from bknd.interviewlab_audio import synthesize_if_enabled
from bknd.interviewlab_engine import start_interview
from bknd.interviewlab_openai import get_openai_client
from fntnd.interviewlab_errors import display_openai_error
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


def _handle_start_interview(api_key: str) -> None:
    if not api_key:
        st.error("Please enter your OpenAI API key to begin.")
        return
    if not st.session_state.get("target_role", "").strip():
        st.error("Please enter a job title.")
        return

    try:
        client = get_openai_client(api_key)
        state = state_from_session(st.session_state)
        first_message = start_interview(state, client)
        state.last_tts_audio = synthesize_if_enabled(
            client, first_message, state.ai_voice_enabled
        )
        apply_state_to_session(state, st.session_state)
        st.session_state.pop("_start_requested", None)
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)


def main() -> None:
    init_session_state()
    inject_styles()

    interview_active = st.session_state.get("interview_active", False)
    interview_complete = st.session_state.get("interview_complete", False)

    if st.session_state.pop("_start_requested", False):
        _handle_start_interview(get_api_key_from_session())

    if interview_complete:
        render_evaluation_view()
        st.divider()
        with st.expander("Full interview transcript"):
            render_chat_history()
    elif interview_active:
        api_key = get_api_key_from_session()
        if not api_key:
            st.error("Your API key was cleared. Please go back and re-enter it.")
            if st.button("Back to Setup"):
                reset_runtime_session()
                st.rerun()
            return
        render_interview_view(api_key)
    else:
        render_setup_view()

        if not interview_active and not interview_complete:
            with st.container():
                st.markdown("<br>", unsafe_allow_html=True)
                _, reset_col, _ = st.columns([3, 1, 3])
                with reset_col:
                    if st.button("Reset", use_container_width=True):
                        reset_runtime_session()
                        st.rerun()
