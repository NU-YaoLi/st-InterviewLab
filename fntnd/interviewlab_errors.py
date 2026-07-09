"""
User-friendly OpenAI error messages for the Streamlit UI.

Used by frontend views so Streamlit Cloud users see actionable feedback instead
of raw stack traces when API calls fail.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import streamlit as st
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)

SERVICE_UNAVAILABLE_MESSAGE = (
    "The interview service is temporarily unavailable. Please try again later."
)


def debug_enabled() -> bool:
    """Optional verbose error details via Streamlit secrets or env DEBUG=true."""
    try:
        return bool(st.secrets.get("DEBUG"))
    except Exception:
        pass
    return os.environ.get("DEBUG", "").strip().lower() in {"1", "true", "yes"}


def display_openai_error(exc: Exception) -> None:
    """Render a friendly ``st.error`` (and optional details) for OpenAI failures."""
    if isinstance(exc, AuthenticationError):
        st.error(
            "**Service unavailable.** Unable to start the interview service right now. "
            "Please try again later."
        )
    elif isinstance(exc, PermissionDeniedError):
        st.error(
            "**Service unavailable.** This interview mode is not available right now. "
            "Please try again later."
        )
    elif isinstance(exc, RateLimitError):
        st.error(
            "**Too many requests.** The service is busy. Wait a moment and try again."
        )
    elif isinstance(exc, APITimeoutError):
        st.error(
            "**Request timeout.** The service took too long to respond. Try again with a shorter answer "
            "or check your network connection."
        )
    elif isinstance(exc, APIConnectionError):
        st.error(
            "**Connection error.** Could not reach the interview service. "
            "Check your network, VPN, or firewall."
        )
    elif isinstance(exc, BadRequestError):
        raw_msg = str(exc)
        msg = raw_msg.lower()
        if "model" in msg and ("not found" in msg or "does not exist" in msg):
            st.error(
                "**Service unavailable.** This interview mode is not available right now. "
                "Please try again later."
            )
        elif "audio" in msg or "transcription" in msg:
            st.error(
                "**Audio error.** Could not process the recording. Try again and speak clearly in English."
            )
        else:
            st.error("**Bad request.** The service could not process that request.")
        if debug_enabled():
            st.info(f"**Details:** {raw_msg}")
    elif isinstance(exc, OpenAIError):
        st.error("**Service error.** Something went wrong. Please try again.")
    elif isinstance(exc, (ValueError, RuntimeError)):
        st.error(SERVICE_UNAVAILABLE_MESSAGE)
    else:
        st.error(f"**Unexpected error:** {exc}")

    if debug_enabled():
        st.exception(exc)


@st.dialog("Cannot start interview")
def show_validation_error(message: str) -> None:
    """Show a centered modal so setup validation errors are impossible to miss."""
    st.error(message)
    if st.button("OK", type="primary", use_container_width=True):
        st.session_state.pop("_validation_error", None)
        st.rerun(scope="app")


def queue_validation_error(message: str) -> None:
    """Store an error to show on the setup page after leaving the generating overlay."""
    st.session_state["_validation_error"] = message


def show_queued_validation_error() -> None:
    """Open the validation dialog when a queued message is present."""
    message = st.session_state.get("_validation_error")
    if message:
        show_validation_error(message)


@st.dialog("End this interview?")
def show_end_interview_confirmation(on_confirm: Callable[[], None]) -> None:
    """Centered confirmation before ending a mock interview early."""
    st.markdown(
        "Are you sure you want to end your mock interview now? "
        "You'll receive feedback based on what you've answered so far."
    )
    no_col, yes_col = st.columns(2)
    with no_col:
        if st.button("No", use_container_width=True):
            st.session_state.pop("_show_end_interview_confirm", None)
            st.rerun(scope="app")
    with yes_col:
        if st.button("Yes, end interview", type="primary", use_container_width=True):
            st.session_state.pop("_show_end_interview_confirm", None)
            on_confirm()


@st.dialog("Preparing your mock interview")
def show_generating_dialog(prepare_callback) -> None:
    """Centered modal shown while the first interview question is generated."""
    st.markdown(
        "Tailoring questions to your role and background, then generating "
        "your first question."
    )
    with st.spinner("Please wait…"):
        if st.session_state.get("_generating_worker_started"):
            prepare_callback()
        else:
            st.session_state["_generating_worker_started"] = True
            st.rerun(scope="app")
