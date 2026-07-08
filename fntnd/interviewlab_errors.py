"""
User-friendly OpenAI error messages for the Streamlit UI.

Used by frontend views so Streamlit Cloud users see actionable feedback instead
of raw stack traces when API calls fail.
"""

from __future__ import annotations

import os

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
            "**Authentication error.** Your OpenAI API key is missing, invalid, "
            "or revoked. Re-enter a valid key in the sidebar."
        )
    elif isinstance(exc, PermissionDeniedError):
        st.error(
            "**Permission denied.** Your API key cannot access the configured model. "
            "Check your OpenAI plan or try a different model in `interviewlab_config.py`."
        )
    elif isinstance(exc, RateLimitError):
        st.error(
            "**Rate limit reached.** OpenAI throttled the request. Wait a moment and try again, "
            "or check usage limits on your OpenAI account."
        )
    elif isinstance(exc, APITimeoutError):
        st.error(
            "**Request timeout.** OpenAI took too long to respond. Try again with a shorter answer "
            "or check your network connection."
        )
    elif isinstance(exc, APIConnectionError):
        st.error(
            "**Connection error.** Could not reach OpenAI. Check your network, VPN, or firewall."
        )
    elif isinstance(exc, BadRequestError):
        raw_msg = str(exc)
        msg = raw_msg.lower()
        if "model" in msg and ("not found" in msg or "does not exist" in msg):
            st.error(
                "**Model unavailable.** The configured model is not enabled for your API key. "
                "Update model names in `interviewlab_config.py`."
            )
        elif "audio" in msg or "transcription" in msg:
            st.error(
                "**Audio error.** Could not process the recording. Try again or switch to Text Only mode."
            )
        else:
            st.error("**Bad request.** OpenAI rejected the request payload.")
        st.info(f"**OpenAI says:** {raw_msg}")
    elif isinstance(exc, OpenAIError):
        st.error(f"**OpenAI error:** {exc}")
    elif isinstance(exc, (ValueError, RuntimeError)):
        st.error(str(exc))
    else:
        st.error(f"**Unexpected error:** {exc}")

    if debug_enabled():
        st.exception(exc)
