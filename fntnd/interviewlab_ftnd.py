"""
Top-level Streamlit UI for InterviewLab.

Defines ``main()`` (invoked by ``interviewlab_main.py``) which renders the full
flow: sidebar setup, API key entry, interview chat, and evaluation dashboard.
"""

from __future__ import annotations

import streamlit as st

from bknd.interviewlab_audio import synthesize_if_enabled
from bknd.interviewlab_engine import start_interview
from bknd.interviewlab_openai import get_openai_client
from fntnd.interviewlab_state import (
    apply_state_to_session,
    get_api_key_from_session,
    init_session_state,
    reset_runtime_session,
    state_from_session,
)
from fntnd.views.interviewlab_evaluation_view import render_evaluation_view
from fntnd.views.interviewlab_interview_view import render_chat_history, render_interview_view
from fntnd.interviewlab_errors import display_openai_error
from fntnd.views.interviewlab_landing_view import render_landing_view
from interviewlab_config import APP_TITLE, INPUT_MODES, INTERVIEW_MODES


def _render_sidebar() -> str:
    """Render setup controls; return the user-entered API key."""
    st.sidebar.title("Interview Setup")

    st.session_state["openai_api_key"] = st.sidebar.text_input(
        "OpenAI API Key",
        type="password",
        value=st.session_state.get("openai_api_key", ""),
        help="Enter your key here. Stored only in this browser session — never in code.",
        placeholder="sk-…",
    )
    api_key = get_api_key_from_session()
    if not api_key:
        st.sidebar.warning("Enter your OpenAI API key to begin.")

    st.sidebar.divider()

    st.session_state["interview_mode"] = st.sidebar.selectbox(
        "Interview Mode",
        INTERVIEW_MODES,
        index=INTERVIEW_MODES.index(st.session_state.get("interview_mode", "Behavioral")),
    )

    st.session_state["target_role"] = st.sidebar.text_input(
        "Target Role",
        value=st.session_state.get("target_role", ""),
        placeholder="e.g., Software Engineer, Data Engineer",
    )

    st.session_state["target_level"] = st.sidebar.text_input(
        "Level",
        value=st.session_state.get("target_level", ""),
        placeholder="e.g., Junior, Mid, Senior",
    )

    st.session_state["job_description"] = st.sidebar.text_area(
        "Job Description",
        value=st.session_state.get("job_description", ""),
        height=120,
        placeholder="Paste the target job description…",
    )

    st.session_state["resume"] = st.sidebar.text_area(
        "Resume / Profile",
        value=st.session_state.get("resume", ""),
        height=120,
        placeholder="Paste your resume or profile summary…",
    )

    st.sidebar.divider()

    st.session_state["input_mode"] = st.sidebar.radio(
        "Input Mode",
        INPUT_MODES,
        index=INPUT_MODES.index(st.session_state.get("input_mode", "Audio + Text")),
    )

    st.session_state["ai_voice_enabled"] = st.sidebar.toggle(
        "AI Voice Response (TTS)",
        value=st.session_state.get("ai_voice_enabled", False),
        help="Play interviewer questions as synthesized speech.",
    )

    st.sidebar.divider()

    col_start, col_reset = st.sidebar.columns(2)
    with col_start:
        start_clicked = st.button(
            "Start Interview",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.get("interview_active", False),
        )
    with col_reset:
        reset_clicked = st.button("Reset", use_container_width=True)

    if reset_clicked:
        reset_runtime_session()
        st.rerun()

    if start_clicked:
        _handle_start_interview(api_key)

    return api_key


def _handle_start_interview(api_key: str) -> None:
    if not api_key:
        st.sidebar.error("OpenAI API key is required.")
        return
    if not st.session_state.get("target_role", "").strip():
        st.sidebar.error("Please enter a target role.")
        return

    try:
        client = get_openai_client(api_key)
        state = state_from_session(st.session_state)
        first_message = start_interview(state, client)
        state.last_tts_audio = synthesize_if_enabled(
            client, first_message, state.ai_voice_enabled
        )
        apply_state_to_session(state, st.session_state)
        st.rerun()
    except Exception as exc:
        display_openai_error(exc)


def main() -> None:
    init_session_state()

    st.title(f"🎙️ {APP_TITLE}")

    api_key = _render_sidebar()

    if not api_key and not st.session_state.get("interview_active"):
        st.info("Enter your OpenAI API key in the sidebar to get started.")

    interview_active = st.session_state.get("interview_active", False)
    interview_complete = st.session_state.get("interview_complete", False)

    if interview_complete:
        st.success("Interview complete! Review your results below.")
        render_evaluation_view()
        st.divider()
        with st.expander("Interview transcript"):
            render_chat_history()
    elif interview_active:
        if not api_key:
            st.error("Your API key was cleared. Re-enter it in the sidebar to continue.")
            return
        render_interview_view(api_key)
    else:
        render_landing_view()
